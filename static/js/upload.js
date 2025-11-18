function uploadZone() {
    return {
        file: null,
        filename: "",
        progress: 0,
        drag: false,
        picked(e) {
            this.file = e.target.files[0];
            this.filename = this.file ? this.file.name : "";
        },
        onDrop(event) {
            const f = event.dataTransfer.files[0];
            if (f && f.type === "application/pdf") {
                this.file = f; this.filename = f.name;
            }
            this.drag = false;
        },
        async submit() {
            if (!this.file) return;
            const form = new FormData();
            form.append("pdf", this.file);

            const xhr = new XMLHttpRequest();
            xhr.open("POST", "/upload");
            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                    this.progress = Math.round((e.loaded / e.total) * 100);
                }
            };
            xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    window.location.href = xhr.responseURL;
                } else {
                    alert("Falha no upload.");
                    this.progress = 0;
                }
            };
            xhr.send(form);
        }
    }
}
