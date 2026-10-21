const loginForm = document.getElementById("login-form");
const message = document.getElementById("message");

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    message.textContent = "";

    try {
        const response = await fetch("/api/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        });

        const result = await response.json();

        if (!response.ok) {
            message.textContent = result.error;
            return;
        }

        window.location.href = result.redirect;
        
    } catch(error) {
        message.textContent = "通信エラーが発生しました。";
    }
});