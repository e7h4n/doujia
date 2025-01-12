window.toggleGroup = function (groupId) {
    const content = document.getElementById(groupId);
    const style = getComputedStyle(content);
    if (style.display === "none") {
        content.style.display = "block";
    } else {
        content.style.display = "none";
    }
};

export default {
    onExtensionPageLoad(ctx) {
    }
}
