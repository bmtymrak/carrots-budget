// Yearly budget page functionality
document.addEventListener('DOMContentLoaded', function() {
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    const csrftoken = getCookie('csrftoken');
    const rollovers = document.querySelectorAll(".rollover-edit");

    function saveRollover(event) {
        const key = event.key;
        if (key === "Enter" || event.type === 'blur') {
            event.preventDefault();
            const targ = event.currentTarget.value;
            const rolloverUpdateUrl = event.currentTarget.dataset.updateUrl;
            const year = event.currentTarget.dataset.year;
            
            fetch(rolloverUpdateUrl, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrftoken,
                },
                body: JSON.stringify({
                    'amount': targ,
                    'category': event.currentTarget.dataset.category,
                    "year": year,
                })
            });
        }
    }

    rollovers.forEach((item) => {
        item.addEventListener('keydown', (event) => {
            const key = event.key;
            saveRollover(event);
        });
        item.addEventListener('blur', saveRollover);
    });

    const monthYtdSelect = document.querySelector(".month-select");
    if (monthYtdSelect) {
        const monthYtd = monthYtdSelect.dataset.selectedMonth;
        monthYtdSelect.selectedIndex = `${monthYtd - 1}`;
        monthYtdSelect.onchange = function() {
            const requestPath = monthYtdSelect.dataset.requestPath;
            window.location = `${requestPath}?ytd=${this.value}`;
        };
    }
});
