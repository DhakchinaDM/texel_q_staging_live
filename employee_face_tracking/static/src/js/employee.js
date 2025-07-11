/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class EmployeeFaceTracking extends Component {
    static template = "employee_face_tracking.OdooServices";
    setup() {
        this.rpc = useService("rpc");

        this.state = useState({
            message: "",
        });

        this.videoRef = useRef("video");
        this.barcodeRef = useRef("barcode");
        this.statusRef = useRef("status");


        onMounted(() => {
            this.startCamera();
            this.barcodeRef.el.focus();
        });
    }

    startCamera() {
        const video = this.videoRef.el;
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(stream => { video.srcObject = stream; })
            .catch(() => { this.state.message = "Camera access denied."; });
    }

    onBarcodeEnter(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            const barcode = ev.target.value.trim();
            if (barcode) {
                this.captureAndSend(barcode);
                ev.target.value = "";
            }
        }
    }


   captureAndSend(barcode) {
        const video = this.videoRef.el;
        const canvas = document.createElement("canvas");
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0);
        const imageData = canvas.toDataURL("image/png");

        this.rpc("/mark/attendance", { barcode, image_data: imageData })
            .then(res => {
                this.state.message = res.message;

                // Wait for 4 seconds then reload the screen
                setTimeout(() => {
                    window.location.reload();
                }, 3000);
            })
            .catch(() => {
                this.state.message = "Error marking attendance.";
            });
    }

}

registry.category("actions").add("employee_face_tracking.OdooServices", EmployeeFaceTracking);
export default EmployeeFaceTracking;
