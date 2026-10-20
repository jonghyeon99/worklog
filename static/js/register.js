
document.getElementById("register-form")
    .addEventListener("submit", async (event) => {
        event.preventDefault();

        const username = document.getElementById("username").value;
        const password = document.getElementById("password").value;
        const passwordConfirm =
            document.getElementById("password-confirm").value;
        const result = document.getElementById("result");

        result.textContent = "";

        if (password !== passwordConfirm) {
            result.textContent = "パスワードが一致しません。";
            return;
        }

        try {
            const response = await fetch("/api/register", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    username: username,
                    password: password,
                    password_confirm: passwordConfirm
                })
            });

            const data = await response.json();

            if (response.ok) {
                result.textContent = data.message;
                document.getElementById("register-form").reset();
            } else {
                result.textContent = data.error;
            }

        } catch (error) {
            result.textContent =
                "サーバーとの通信中にエラーが発生しました。";
        }
    });
