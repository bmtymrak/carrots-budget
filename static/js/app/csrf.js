(function () {
    window.CarrotsBudget = window.CarrotsBudget || {}

    function getCookie(name) {
        if (!document.cookie) {
            return null
        }

        const cookies = document.cookie.split(";")

        for (const cookieString of cookies) {
            const cookie = cookieString.trim()

            if (cookie.substring(0, name.length + 1) === `${name}=`) {
                return decodeURIComponent(cookie.substring(name.length + 1))
            }
        }

        return null
    }

    window.CarrotsBudget.getCsrfToken = function () {
        const metaToken = document.querySelector('meta[name="csrf-token"]')

        return metaToken ? metaToken.content : getCookie("csrftoken")
    }
})()
