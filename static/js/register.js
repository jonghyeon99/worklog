
document.getElementById("register-form")
    .addEventListener("submit", async (event) => {
        event.preventDefault();

        const form = document.getElementById("register-form");
        const username = document.getElementById("username").value;
        const password = document.getElementById("password").value;
        const passwordConfirm = document.getElementById("password-confirm").value;
        const result = document.getElementById("result");
        const submitButton = form.querySelector('button[type="submit"]');

        result.textContent = "";
        result.style.color = "";

        if (password !== passwordConfirm) {
            result.textContent = "パスワードが一致しません。";
            return;
        }

        submitButton.disabled = true;

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
                result.textContent =
                    "登録が完了しました。2秒後にログイン画面へ移動します。";
                result.style.color = "#16803c";

                form.reset();

                setTimeout(() => {
                    window.location.replace("/login");
                }, 2000);

            } else {
                result.textContent =
                    data.error || "登録に失敗しました。";

                submitButton.disabled = false;
            }

        } catch (error) {
            result.textContent =
                "サーバーとの通信中にエラーが発生しました。";

            submitButton.disabled = false;
        }
    });
