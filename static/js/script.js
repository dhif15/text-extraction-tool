document.addEventListener("DOMContentLoaded", function () {
    const uploadButton = document.querySelector("button");
    const fileInput = document.createElement("input");
    const uploadArea = document.querySelector(".upload-container"); // اختيار المنطقة المستهدفة لتحديثها

    fileInput.type = "file";
    fileInput.style.display = "none";

    // Trigger the file input when upload button is clicked
    uploadButton.addEventListener("click", () => {
        fileInput.click();
    });

    // Handle file upload
    fileInput.addEventListener("change", () => {
        const formData = new FormData();
        formData.append("file", fileInput.files[0]);

        // Update the upload area to show loading spinner
        uploadArea.innerHTML = `
            <div class="upload-area">
                <img src="/static/images/loading.gif" alt="Loading" class="loading-icon" />
                <p class="processing-text">جاري استخراج النصوص...</p>
            </div>
        `;

        // Send the file to the server
        fetch("/", {
            method: "POST",
            body: formData,
        })
            .then((response) => response.json()) // Parse JSON response
            .then((data) => {
                if (data.redirect) {
                    window.location.href = data.redirect; // Redirect to /process
                } else if (data.error) {
                    alert("Error: " + data.error); // Show error message
                    window.location.reload();
                }
            })
            .catch((error) => {
                console.error("Error:", error);
                alert("An unexpected error occurred. Please try again.");
                window.location.reload();
            });
    });
});
