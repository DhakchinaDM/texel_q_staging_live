/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import attendanceApp from "@hr_attendance/public_kiosk/public_kiosk_app";
import { useService } from "@web/core/utils/hooks";

const MODEL_URL = '/sttl_face_attendance/static/face-api/weights/';
let faceModelsLoaded = false;

patch(attendanceApp.kioskAttendanceApp.prototype, {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
    },

    initiateFaceAttendance: async function () {
        await this.setupCamera();
    },

    async onManualSelection(employeeId) {
        await this.setupCamera(employeeId);
    },

    async setupCamera(employeeId = null) {
        if (!faceModelsLoaded) {
            await Promise.all([
                faceapi.nets.tinyFaceDetector.load(MODEL_URL),
                faceapi.nets.faceLandmark68Net.load(MODEL_URL),
                faceapi.nets.faceRecognitionNet.load(MODEL_URL),
            ]);
            faceModelsLoaded = true;
        }

        return new Promise(async (resolve) => {
            const overlay = this._createOverlay();
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                const video = this._setupVideoStream(stream, overlay);
                this._bindAutoCapture(video, overlay, resolve, employeeId);
                this._addEventListeners(video, overlay, resolve);
            } catch (error) {
                alert("Unable to access the camera");
                this._handleError(null, overlay, resolve);
            }
        });
    },

    async _bindAutoCapture(video, overlay, resolve, employeeId) {
        let attempts = 0;
        const employeeDetails = await this.rpc('/employee/images', { employee_id: employeeId });

        const attemptCapture = async () => {
            if (attempts++ >= 5) {
                alert('No matching employee found.');
                this._handleError(video, overlay, resolve);
                return;
            }

            try {
                const faceDetection = await faceapi.detectSingleFace(video, new faceapi.TinyFaceDetectorOptions())
                    .withFaceLandmarks()
                    .withFaceDescriptor();

                if (!faceDetection) {
                    setTimeout(attemptCapture, 5000);
                    return;
                }

                const matchingEmployeeId = await this._findMatchingEmployee(faceDetection, employeeDetails);
                if (matchingEmployeeId) {
                    await this._handleEmployeeDetected(matchingEmployeeId, video, overlay, resolve);
                    return;
                }

                setTimeout(attemptCapture, 5000);
            } catch (error) {
                alert('Face detection failed.');
                this._handleError(video, overlay, resolve);
            }
        };

        attemptCapture();
    },

    _createOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'camera_overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        document.body.appendChild(overlay);
        return overlay;
    },

    _setupVideoStream(stream, overlay) {
        const camDiv = document.createElement('div');
        camDiv.id = 'cam-div';
        overlay.appendChild(camDiv);

        const video = document.createElement('video');
        video.id = 'camera-stream';
        camDiv.appendChild(video);

        const closeButton = document.createElement('button');
        closeButton.id = 'close-button';
        closeButton.textContent = 'Close Camera';
        closeButton.style.marginTop = '10px';
        camDiv.appendChild(closeButton);

        video.srcObject = stream;
        video.play();

        return video;
    },

    _addEventListeners(video, overlay, resolve) {
        document.getElementById('close-button').addEventListener('click', () => {
            this._handleError(video, overlay, resolve);
        });
    },

    async _findMatchingEmployee(faceDetection, employeeDetails) {
        for (const { employee_id, image, name } of employeeDetails) {
            if (!image) continue;

            try {
                const mimeMatch = image.match(/^data:(image\/[a-zA-Z]+);base64,/);
                const mimeType = mimeMatch ? mimeMatch[1] : 'image/png';
                const blob = this._base64ToBlob(image, mimeType);
                const referenceImage = await faceapi.bufferToImage(blob);

                const referenceDescriptor = await faceapi
                    .detectSingleFace(referenceImage, new faceapi.TinyFaceDetectorOptions())
                    .withFaceLandmarks()
                    .withFaceDescriptor();

                if (referenceDescriptor) {
                    const distance = faceapi.euclideanDistance(
                        faceDetection.descriptor,
                        referenceDescriptor.descriptor
                    );
                    if (distance < 0.45) return employee_id;
                }
            } catch (error) {
                console.warn(`Error processing employee ${employee_id} (${name}):`, error);
                continue;
            }
        }

        return null;
    },

    async _handleEmployeeDetected(employeeId, video, overlay, resolve) {
        this.employee_id = employeeId;
        this._stopStream(video);
        overlay.remove();

        const result = await this.makeRpcWithGeolocation('manual_selection', {
            token: this.props.token,
            employee_id: employeeId,
            pin_code: false,
        });

        if (result && result.attendance) {
            this.employeeData = result;
            this.switchDisplay('greet');
        }

        resolve(true);
    },

    _handleError(video, overlay, resolve) {
        if (video) this._stopStream(video);
        if (overlay) overlay.remove();
        resolve(false);
    },

    _stopStream(video) {
        if (video && video.srcObject) {
            video.srcObject.getTracks().forEach((track) => track.stop());
            if (video.parentNode) video.parentNode.remove();
        }
    },

    _base64ToBlob(base64, mimeType) {
        const byteCharacters = atob(base64.split(',')[1] || base64);
        const byteArrays = [];

        for (let offset = 0; offset < byteCharacters.length; offset += 512) {
            const slice = byteCharacters.slice(offset, offset + 512);
            const byteArray = new Uint8Array([...slice].map((char) => char.charCodeAt(0)));
            byteArrays.push(byteArray);
        }

        return new Blob(byteArrays, { type: mimeType });
    },
});
