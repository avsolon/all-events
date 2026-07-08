console.log("All Events Novosibirsk - Aggregator loaded");

document.addEventListener("DOMContentLoaded", function() {
    const cards = document.querySelectorAll(".event-card");
    cards.forEach(card => {
        card.addEventListener("mouseenter", function() {
            this.classList.add("shadow-lg");
        });
        card.addEventListener("mouseleave", function() {
            this.classList.remove("shadow-lg");
        });
    });
});
