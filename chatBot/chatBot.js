const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const userInput = document.getElementById("user-input");
const minimizeBtn = document.getElementById("minimize-btn");
const chatContainer = document.querySelector(".chat-container");
const chatToggle = document.getElementById("chat-toggle");

function appendMessage(sender, message) {
    const messageDiv = document.createElement("div");
    messageDiv.classList.add(sender === "bot" ? "bot-message" : "user-message");

    if (sender === "bot") {
        const botIcon = document.createElement("img");
        botIcon.src = "/assets/images/bot.webp";
        botIcon.alt = "Bot Icon";
        botIcon.classList.add("bot-icon");
        messageDiv.appendChild(botIcon);
    }

    const messageContent = document.createElement("p");
    if (sender === "bot") {
        messageContent.innerHTML = message;
    } else {
        messageContent.textContent = message;
    }

    messageDiv.appendChild(messageContent);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

minimizeBtn.addEventListener("click", () => {
    chatContainer.classList.add("hidden"); // Hide chat container
    chatToggle.classList.remove("hidden"); // Show minimized button
});

// Handle toggle button click
chatToggle.addEventListener("click", () => {
    chatContainer.classList.remove("hidden"); // Show chat container
    chatToggle.classList.add("hidden"); // Hide minimized button
});


chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const message = userInput.value.trim();
    if (!message) return;

    appendMessage("user", message);
    userInput.value = "";

    try {
        const response = await fetch("http://127.0.0.1:5000/chatBot", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message }),
        });

        if (!response.ok) {
            throw new Error("Failed to fetch response");
        }

        const data = await response.json();
        appendMessage("bot", data.reply);
    } catch (error) {
        console.error("Error:", error);
        appendMessage("bot", "Sorry, something went wrong. Please try again.");
    }
});
