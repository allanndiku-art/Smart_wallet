let token = "";

function login() {
    fetch("/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            username: document.getElementById("username").value,
            password: document.getElementById("password").value
        })
    })
    .then(res => res.json())
    .then(data => {
        token = data.token;
        alert("Login successful");
    });
}

function getBalance() {
    fetch("/balance", {
        headers: {"Authorization": token}
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById("balance").innerText =
            "KES " + data.balance;
    });
}

function transfer() {
    fetch("/transfer", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": token
        },
        body: JSON.stringify({
            receiver_id: document.getElementById("receiver").value,
            amount: document.getElementById("amount").value
        })
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message || data.error);
    });
}

function getTransactions() {
    fetch("/transactions", {
        headers: {"Authorization": token}
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById("history").innerText =
            JSON.stringify(data.transactions, null, 2);
    });
}