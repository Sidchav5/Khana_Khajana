function showInput(option) {
    const emailInput = document.getElementById("email-input");
    const phoneInput = document.getElementById("phone-input");

    if (option === "email") {
        emailInput.classList.remove("hidden");
        phoneInput.classList.add("hidden");
    } else if (option === "phone") {
        phoneInput.classList.remove("hidden");
        emailInput.classList.add("hidden");
    }
}
