import datetime
import calendar
from decimal import Decimal

from django.db.models import Sum, Q, Value, DecimalField, F, ExpressionWrapper
from django.db.models.functions import Coalesce

from budgets.models import BudgetItem, Rollover, YearlyBudget, MonthlyBudget
from purchases.models import Purchase, Income


class BudgetService:
    def get_monthly_budget_context(self, user, year: int, month: int) -> dict:
        monthly_budget = MonthlyBudget.objects.get(
            date__year=year,
            date__month=month,
            user=user,
        )

        category_purchases = Purchase.objects.filter(
            date__year=year,
            date__month=month,
            user=user,
        ).values("category").annotate(total=Sum("amount"))

        category_incomes = Income.objects.filter(
            date__year=year,
            date__month=month,
            user=user,
        ).values("category").annotate(total=Sum("amount"))

        purchases_data = {
            item['category']: item['total']
            for item in category_purchases
        }

        incomes_data = {
            item['category']: item['total']
            for item in category_incomes
        }

        budget_items = BudgetItem.objects.filter(
            user=user,
            monthly_budget=monthly_budget,
            savings=False
        ).select_related('category').order_by("category__name")

        savings_items = BudgetItem.objects.filter(
            user=user,
            monthly_budget=monthly_budget,
            savings=True
        ).select_related('category').order_by("category__name")

        # Process Spending Items
        budget_items_list = []
        total_spending_budgeted = 0
        total_spending_spent = 0
        total_spending_remaining = 0

        for item in budget_items:
            category_id = item.category.id
            spent = purchases_data.get(category_id, 0) or 0
            income = incomes_data.get(category_id, 0) or 0
            diff = item.amount - spent + income

            item.spent = spent
            item.income = income
            item.diff = diff
            
            budget_items_list.append(item)

            total_spending_budgeted += item.amount
            total_spending_spent += spent
            total_spending_remaining += diff

        # Process Savings Items
        savings_items_list = []
        total_savings_budgeted = 0
        total_saved = 0
        total_savings_remaining = 0

        for item in savings_items:
            category_id = item.category.id
            spent = purchases_data.get(category_id, 0) or 0
            income = incomes_data.get(category_id, 0) or 0
            
            # For savings, "saved" amounts come from purchases (transfers out) and direct income
            saved = spent + income
            diff = item.amount - saved + income 
            
            item.saved = saved
            item.income = income
            item.diff = diff
            
            savings_items_list.append(item)

            total_savings_budgeted += item.amount
            total_saved += saved
            total_savings_remaining += diff

        # Uncategorized Purchases
        uncategorized_amount = Purchase.objects.filter(
            user=user,
            category__name=None,
            date__month=month,
            date__year=year,
        ).aggregate(amount=Sum("amount"))["amount"] or 0

        uncategorized_purchases = {
            "amount": uncategorized_amount,
            "remaining": (0 - uncategorized_amount),
            "budgeted": 0,
        }

        # Totals Adjustment
        total_spending_spent += uncategorized_amount
        total_spending_remaining -= uncategorized_amount

        total_budgeted = total_spending_budgeted + total_savings_budgeted
        total_spent_saved = total_spending_spent + total_saved
        total_remaining = total_spending_remaining + total_savings_remaining

        # Income Processing
        incomes_query = Income.objects.filter(
            user=user,
            date__month=month,
            date__year=year,
        ).order_by("date", "source").prefetch_related("category")
        
        total_income_val = incomes_query.filter(category=None).aggregate(amount=Sum("amount"))["amount"] or 0
        free_income = total_income_val - total_spent_saved
        total_income = {"amount": total_income_val}

        purchases_list = Purchase.objects.filter(
            user=user,
            date__year=year,
            date__month=month,
        ).order_by("date", "source").prefetch_related("category")

        return {
            "budget_items": budget_items_list,
            "savings_items": savings_items_list,
            "purchases": purchases_list,
            "incomes": incomes_query,
            "total_budgeted": total_budgeted,
            "total_spent": total_spending_spent,
            "total_spent_saved": total_spent_saved,
            "total_spending_budgeted": { "amount": total_spending_budgeted },
            "total_spending_spent": { "amount": total_spending_spent },
            "total_spending_remaining": { "amount": total_spending_remaining },
            "total_remaining": total_remaining,
            "total_saved": { "amount": total_saved },
            "total_savings_budgeted": { "amount": total_savings_budgeted },
            "total_savings_remaining": { "amount": total_savings_remaining },
            "total_income": total_income,
            "free_income": free_income,
            "uncategorized_purchases": uncategorized_purchases,
            "months": [
                (calendar.month_name[m], m) for m in range(1, 13)
            ],
        }

    def get_yearly_budget_context(self, user, year: int, ytd_month: int) -> dict:
        """
        Orchestrates the gathering of all budget data for the YearlyBudgetDetailView.
        """
        
        purchases = Purchase.objects.filter(
            user=user,
            date__year=year,
        )

        purchases_uncategorized = purchases.filter(category=None)

        incomes = Income.objects.filter(
            user=user,
            date__year=year,
        )

        purchases_data = {
            item['category']: {'total': item['total'], 'total_ytd': item['total_ytd']}
            for item in purchases.values('category').annotate(
                total=Sum('amount'),
                total_ytd=Sum('amount', filter=Q(date__month__lte=ytd_month))
            )
        }
        
        incomes_data = {
            item['category']: {'total': item['total'], 'total_ytd': item['total_ytd']}
            for item in incomes.values('category').annotate(
                total=Sum('amount'),
                total_ytd=Sum('amount', filter=Q(date__month__lte=ytd_month))
            )
        }
        
        rollovers_by_category = dict(
            Rollover.objects.filter(
                user=user,
                yearly_budget__date__year=year - 1,
            ).values_list('category', 'amount')
        )

        budget_items_context = self._process_spending_items(
            user, year, ytd_month, purchases_data, incomes_data, rollovers_by_category
        )

        savings_items_context = self._process_savings_items(
            user, year, ytd_month, purchases_data, incomes_data, rollovers_by_category
        )
        
        # Calculate Global Totals
        total_budgeted = budget_items_context['total_spending_budgeted'] + savings_items_context['total_savings_budgeted']
        total_spent_saved = budget_items_context['total_spending_spent'] + savings_items_context['total_saved']
        total_remaining = budget_items_context['total_spending_remaining'] + savings_items_context['total_savings_remaining']
        total_remaining_current_year = (
            budget_items_context['total_spending_remaining_current_year'] + savings_items_context['total_savings_remaining']
        )

        total_budgeted_ytd = budget_items_context['total_spending_budgeted_ytd'] + savings_items_context['total_savings_budgeted_ytd']
        total_spent_saved_ytd = budget_items_context['total_spending_spent_ytd'] + savings_items_context['total_saved_ytd']
        total_remaining_ytd = budget_items_context['total_spending_remaining_ytd'] + savings_items_context['total_savings_remaining_ytd']

        income_context = self._process_income_totals(incomes, ytd_month, total_spent_saved, total_spent_saved_ytd, total_budgeted, total_budgeted_ytd)
        
        free_income = budget_items_context['free_income_spending'] + savings_items_context['free_income_savings']

        rollovers = (
            Rollover.objects.filter(user=user, yearly_budget__date__year=year)
            .prefetch_related("category")
            .order_by("category__name")
        )
        
        savings_category_ids = savings_items_context['savings_category_ids']
        rollovers_spending = []
        rollovers_savings = []
        
        for rollover in rollovers:
            if rollover.category.id in savings_category_ids:
                rollovers_savings.append(rollover)
            else:
                rollovers_spending.append(rollover)

        context = {
            "incomes": incomes,
            "purchases_uncategorized": purchases_uncategorized,
            "rollovers_spending": rollovers_spending,
            "rollovers_savings": rollovers_savings,
            
            "total_budgeted": total_budgeted,
            "total_spent_saved": total_spent_saved,
            "total_remaining": total_remaining,
            "total_remaining_current_year": total_remaining_current_year,
            
            "total_budgeted_ytd": total_budgeted_ytd,
            "total_spent_saved_ytd": total_spent_saved_ytd,
            "total_remaining_ytd": total_remaining_ytd,
            
            "free_income": free_income,
            
            "months": [
                (calendar.month_name[month], month) for month in range(1, 13)
            ],
        }
        
        context.update(budget_items_context)
        context.update(savings_items_context)
        context.update(income_context)
        
        # Remove internal keys that aren't needed in template
        context.pop('savings_category_ids', None)
        context.pop('free_income_spending', None)
        context.pop('free_income_savings', None)

        return context

    def _process_spending_items(self, user, year, ytd_month, purchases_data, incomes_data, rollovers_by_category):
        budgetitems = (
            BudgetItem.objects.filter(user=user)
            .filter(
                monthly_budget__date__year=year,
                savings=False,
            )
            .values("category", "category__name")
            .annotate(
                amount_total=Sum("amount"),
                amount_total_ytd=Sum("amount", filter=Q(monthly_budget__date__month__lte=ytd_month)),
            )
            .order_by("category__name")
        )
        
        budgetitems_list = []
        budgetitems_ytd_list = []
        
        total_spending_spent = 0
        total_spending_remaining = 0
        total_spending_budgeted = 0
        total_spending_remaining_current_year = 0
        free_income_spending = 0
        
        total_spending_spent_ytd = 0
        total_spending_remaining_ytd = 0
        total_spending_budgeted_ytd = 0

        for item in budgetitems:
            category_id = item['category']
            
            purchase_data = purchases_data.get(category_id, {'total': 0, 'total_ytd': 0})
            income_data = incomes_data.get(category_id, {'total': 0, 'total_ytd': 0})
            
            spent = purchase_data['total'] or 0
            income = income_data['total'] or 0
            rollover = rollovers_by_category.get(category_id, 0) or 0
            
            spent_ytd = purchase_data['total_ytd'] or 0
            income_ytd = income_data['total_ytd'] or 0
            amount_total_ytd = item['amount_total_ytd'] or 0
            
            item.update({
                'spent': spent,
                'income': income,
                'rollover': rollover,
                'diff': item['amount_total'] - spent + income + rollover,
                'remaining_current_year': item['amount_total'] - spent + income,
            })
            budgetitems_list.append(item)

            ytd_item = {
                'category': category_id,
                'category__name': item['category__name'],
                'amount_total_ytd': amount_total_ytd,
                'spent': spent_ytd,
                'income': income_ytd,
                'diff_ytd': amount_total_ytd - spent_ytd + income_ytd,
                'remaining_current_year_ytd': amount_total_ytd - spent_ytd + income_ytd,
            }
            budgetitems_ytd_list.append(ytd_item)

            total_spending_spent += spent
            total_spending_remaining += item['diff']
            total_spending_budgeted += item['amount_total']
            total_spending_remaining_current_year += item['remaining_current_year']
            if rollover == 0:
                free_income_spending += item['remaining_current_year']
                
            total_spending_spent_ytd += spent_ytd
            total_spending_remaining_ytd += ytd_item['diff_ytd']
            total_spending_budgeted_ytd += amount_total_ytd
            
        # Combine for template
        budgetitems_dict = {item["category__name"]: item for item in budgetitems_list}
        budgetitems_ytd_dict = {item["category__name"]: item for item in budgetitems_ytd_list}
        
        budget_items_combined = []
        for category_name in budgetitems_dict.keys():
            budget_item = budgetitems_dict[category_name]
            ytd_item = budgetitems_ytd_dict.get(category_name, {
                "amount_total_ytd": 0, "diff_ytd": 0, "spent": 0
            })
            
            budget_items_combined.append((
                {"category__name": category_name},
                {"amount_total": budget_item["amount_total"]},
                {"spent": budget_item["spent"]},
                {"diff": budget_item["diff"]},
                {"amount_total_ytd": ytd_item.get("amount_total_ytd", 0)},
                {"diff_ytd": ytd_item.get("diff_ytd", 0)},
                {"spent": ytd_item.get("spent", 0)},
            ))

        return {
            "budget_items_combined": budget_items_combined,
            "total_spending_spent": total_spending_spent,
            "total_spending_remaining": total_spending_remaining,
            "total_spending_budgeted": total_spending_budgeted,
            "total_spending_remaining_current_year": total_spending_remaining_current_year,
            "total_spending_spent_ytd": total_spending_spent_ytd,
            "total_spending_remaining_ytd": total_spending_remaining_ytd,
            "total_spending_budgeted_ytd": total_spending_budgeted_ytd,
            "free_income_spending": free_income_spending,
        }

    def _process_savings_items(self, user, year, ytd_month, purchases_data, incomes_data, rollovers_by_category):
        savings_items = (
            BudgetItem.objects.filter(
                user=user,
                monthly_budget__date__year=year,
                savings=True,
            )
            .values("category", "category__name")
            .annotate(
                amount_total=Sum("amount"),
                amount_total_ytd=Sum("amount", filter=Q(monthly_budget__date__month__lte=ytd_month)),
            )
            .order_by("category__name")
        )
        
        savings_items_list = []
        savings_items_ytd_list = []
        
        total_saved = 0
        total_savings_remaining = 0
        total_savings_budgeted = 0
        free_income_savings = 0
        
        total_saved_ytd = 0
        total_savings_remaining_ytd = 0
        total_savings_budgeted_ytd = 0
        
        savings_category_ids = set()

        for item in savings_items:
            category_id = item['category']
            savings_category_ids.add(category_id)
            
            p_data = purchases_data.get(category_id, {'total': 0, 'total_ytd': 0})
            i_data = incomes_data.get(category_id, {'total': 0, 'total_ytd': 0})
            
            purchases_amount = p_data['total'] or 0
            income = i_data['total'] or 0
            rollover = rollovers_by_category.get(category_id, 0) or 0
            saved = purchases_amount + income
            
            purchases_amount_ytd = p_data['total_ytd'] or 0
            income_ytd = i_data['total_ytd'] or 0
            saved_ytd = purchases_amount_ytd + income_ytd
            amount_total_ytd = item['amount_total_ytd'] or 0
            
            item.update({
                'income': income,
                'purchases_amount': purchases_amount,
                'saved': saved,
                'rollover': rollover,
                'diff': item['amount_total'] - saved + income,
            })
            savings_items_list.append(item)

            ytd_item = {
                'category': category_id,
                'category__name': item['category__name'],
                'amount_total_ytd': amount_total_ytd,
                'income': income_ytd,
                'purchases_amount': purchases_amount_ytd,
                'saved': saved_ytd,
                'diff_ytd': amount_total_ytd - saved_ytd + income_ytd,
            }
            savings_items_ytd_list.append(ytd_item)

            total_saved += saved
            total_savings_remaining += item['diff']
            total_savings_budgeted += item['amount_total']
            if rollover == 0:
                free_income_savings += item['diff']
                
            total_saved_ytd += saved_ytd
            total_savings_remaining_ytd += ytd_item['diff_ytd']
            total_savings_budgeted_ytd += amount_total_ytd
            
        # Combine for template
        savings_items_dict = {item["category__name"]: item for item in savings_items_list}
        savings_items_ytd_dict = {item["category__name"]: item for item in savings_items_ytd_list}
        
        savings_items_combined = []
        for category_name in savings_items_dict.keys():
            savings_item = savings_items_dict[category_name]
            ytd_item = savings_items_ytd_dict.get(category_name, {
                "amount_total_ytd": 0, "diff_ytd": 0, "saved": 0
            })
            
            savings_items_combined.append((
                {"category__name": category_name},
                {"amount_total": savings_item["amount_total"]},
                {"saved": savings_item["saved"]},
                {"diff": savings_item["diff"]},
                {"amount_total_ytd": ytd_item.get("amount_total_ytd", 0)},
                {"diff_ytd": ytd_item.get("diff_ytd", 0)},
                {"saved": ytd_item.get("saved", 0)},
            ))

        return {
            "savings_items_combined": savings_items_combined,
            "total_saved": total_saved,
            "total_savings_budgeted": total_savings_budgeted,
            "total_savings_remaining": total_savings_remaining,
            "total_saved_ytd": total_saved_ytd,
            "total_savings_budgeted_ytd": total_savings_budgeted_ytd,
            "total_savings_remaining_ytd": total_savings_remaining_ytd,
            "free_income_savings": free_income_savings,
            "savings_category_ids": savings_category_ids,
        }

    def _process_income_totals(self, incomes, ytd_month, total_spent_saved, total_spent_saved_ytd, total_budgeted, total_budgeted_ytd):
        income_aggregates = incomes.aggregate(
            total_income=ExpressionWrapper(
                Coalesce(Sum("amount"), Value(0)), output_field=DecimalField()
            ),
            total_income_ytd=ExpressionWrapper(
                Coalesce(Sum("amount", filter=Q(date__month__lte=ytd_month)), Value(0)), 
                output_field=DecimalField()
            ),
            total_income_budgeted=ExpressionWrapper(
                Coalesce(Sum("amount", filter=Q(category=None)), Value(0)), 
                output_field=DecimalField()
            ),
            total_income_budgeted_ytd=ExpressionWrapper(
                Coalesce(Sum("amount", filter=Q(category=None, date__month__lte=ytd_month)), Value(0)), 
                output_field=DecimalField()
            ),
            total_income_category=ExpressionWrapper(
                Coalesce(Sum("amount", filter=~Q(category=None)), Value(0)), 
                output_field=DecimalField()
            ),
            total_income_category_ytd=ExpressionWrapper(
                Coalesce(Sum("amount", filter=Q(~Q(category=None), date__month__lte=ytd_month)), Value(0)), 
                output_field=DecimalField()
            ),
        )

        total_income = {"amount": income_aggregates["total_income"]}
        total_income_ytd = {"amount": income_aggregates["total_income_ytd"]}
        total_income_budgeted = {"amount": income_aggregates["total_income_budgeted"]}
        total_income_budgeted_ytd = {"amount": income_aggregates["total_income_budgeted_ytd"]}
        total_income_category = {"amount": income_aggregates["total_income_category"]}
        total_income_category_ytd = {"amount": income_aggregates["total_income_category_ytd"]}

        total_income_spent_diff = total_income["amount"] - total_spent_saved
        budgeted_income_spent_diff = total_income_budgeted["amount"] - total_spent_saved
        budgeted_income_spent_diff_ytd = (
            total_income_budgeted_ytd["amount"] - total_spent_saved_ytd
        )

        budgeted_income_diff = total_income_budgeted["amount"] - total_budgeted
        budgeted_income_diff_ytd = (
            total_income_budgeted_ytd["amount"] - total_budgeted_ytd
        )
        
        return {
            "total_income": total_income,
            "total_income_ytd": total_income_ytd,
            "total_income_budgeted": total_income_budgeted,
            "total_income_budgeted_ytd": total_income_budgeted_ytd,
            "total_income_category": total_income_category,
            "total_income_category_ytd": total_income_category_ytd,
            "budgeted_income_diff": budgeted_income_diff,
            "budgeted_income_diff_ytd": budgeted_income_diff_ytd,
            "total_income_spent_diff": total_income_spent_diff,
            "budgeted_income_spent_diff": budgeted_income_spent_diff,
            "budgeted_income_spent_diff_ytd": budgeted_income_spent_diff_ytd,
        }
