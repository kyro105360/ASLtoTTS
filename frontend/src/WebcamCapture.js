import React, { useRef, useEffect, useState } from "react";

const WebcamCapture = () => {
    const videoRef = useRef(null);
    const webSocket = useRef(null);
    const [detectedText, setDetectedText] = useState("Detected text will appear here");
    const [isInitialMessage, setIsInitialMessage] = useState(true); // Add this line

//dummy comment
    useEffect(() => {
        // Initialize WebSocket connection
        webSocket.current = new WebSocket("ws://localhost:8765");
        webSocket.current.onopen = () => console.log("WebSocket Connected");
        webSocket.current.onerror = (error) => console.log("WebSocket Error: ", error);

        // Handle messages received from the server
        webSocket.current.onmessage = (event) => {
            const receivedCharacter = event.data; // `event.data` contains the character sent from the server
            if (receivedCharacter !== "") {
                setDetectedText(prevText => {
                    let word = ""
                    // Check if `prevText` is still the initial message
                    if (prevText === "Detected text will appear here") {
                        // If so, replace it with the received character
                        if (!(receivedCharacter === "\b" ||  receivedCharacter === " "))
                            word = receivedCharacter;
                    } else {
                        if (receivedCharacter === "\b")
                            word = prevText.substring(0, prevText.length-1);
                        else
                            word= `${prevText}${receivedCharacter}`;
                    }
                    if (word === "")
                        return "Detected text will appear here"

                    return word;
                    
                });
            };
        }

        webSocket.current.onclose = () => console.log("WebSocket Disconnected");

        // Get access to the webcam
        if (navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia({ video: true })
                .then((stream) => {
                    if (videoRef.current) {
                        videoRef.current.srcObject = stream;
                    }
                })
                .catch((err) => {
                    console.error("Error accessing the webcam", err);
                });
        }
        return () => {
            if (webSocket.current) {
                webSocket.current.close();
            }
        };
    }, []);

    useEffect(() => {
        if (!webSocket.current) return;

        const intervalId = setInterval(() => {
            captureAndSendFrame();
        }, 2000); // Adjust the interval as needed

        return () => clearInterval(intervalId);
    }, [webSocket.current]); // Re-run the effect if the WebSocket connection changes

    const captureAndSendFrame = () => {
        if (videoRef.current && webSocket.current.readyState === WebSocket.OPEN) {
            const canvas = document.createElement("canvas");
            canvas.width = videoRef.current.videoWidth;
            canvas.height = videoRef.current.videoHeight;
            const context = canvas.getContext("2d");
            context.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
            canvas.toBlob((blob) => {
                webSocket.current.send(blob); // Send the frame as a Blob over the WebSocket
            }, "image/jpeg");
        }
    };

    // Function to speak the detected text
    const speak = (text) => {
        const speech = new SpeechSynthesisUtterance(text);
        window.speechSynthesis.speak(speech);
    };

    // Handler for clicking the speaker icon
    const handleSpeakerIconClick = () => {
        speak(detectedText);
    };

    const handleTextChange = (event) => {
        // Here we check if the initial message flag is set, and if so, clear the text
        if (isInitialMessage) {
            setDetectedText(event.target.value.replace("Detected text will appear here", ""));
            setIsInitialMessage(false); // Reset the flag as soon as the user starts typing
        } else {
            setDetectedText(event.target.value);
        }
    };

    return (
        <div className="WebcamOutputContainer">
            <div className="WebcamFeed">
                <video ref={videoRef} autoPlay playsInline />
            </div>
            <div className="OutputText">
                <textarea
                    value={detectedText}
                    onChange={handleTextChange}
                    onFocus={() => isInitialMessage && setDetectedText("")} // Clear text when the textarea is focused if it"s the initial message
                />
                <span className="material-symbols-outlined" onClick={handleSpeakerIconClick}>
                    volume_up
                </span>
            </div>
        </div>
    );
};

export default WebcamCapture;