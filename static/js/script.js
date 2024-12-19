// document.addEventListener("DOMContentLoaded", function () {
//     const uploadButton = document.querySelector("button");
//     const fileInput = document.createElement("input");

//     fileInput.type = "file";
//     fileInput.style.display = "none";

//     // Trigger the file input when upload button is clicked
//     uploadButton.addEventListener("click", () => {
//         fileInput.click();
//     });

//     // Handle file upload
//     fileInput.addEventListener("change", () => {
//         const formData = new FormData();
//         formData.append("file", fileInput.files[0]);

//         // Show loading spinner
//         document.body.innerHTML = `
//             <div style="text-align: center; margin-top: 20%">
//                 <img src="/static/images/loading.gif" alt="Loading..." width="80px" />
//                 <p style="font-size: 20px; color: #333;">جاري استخراج النصوص...</p>
//             </div>
//         `;

//         // Send the file to the server
//         fetch("/", {
//             method: "POST",
//             body: formData,
//         })
//             .then((response) => {
//                 if (response.redirected) {
//                     // Redirect to process result page
//                     window.location.href = response.url;
//                 } else {
//                     alert("Error processing file. Please try again.");
//                 }
//             })
//             .catch((error) => {
//                 console.error("Error:", error);
//                 alert("An unexpected error occurred. Please try again.");
//             });
//     });
// });


document.addEventListener("DOMContentLoaded", function () {
    const uploadButton = document.querySelector("button");
    const fileInput = document.createElement("input");

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

        // Show loading spinner
        document.body.innerHTML = `
            <div style="text-align: center; margin-top: 20%">
                <img src="/static/images/loading.gif" alt="Loading..." width="80px" />
                <p style="font-size: 20px; color: #333;">جاري استخراج النصوص...</p>
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
