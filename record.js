let mediaRecorder = null;

function start_recording() {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        console.log("getUserMedia supported.");
        navigator.mediaDevices
            .getUserMedia({ audio: {
                channelCount: 1,
                sampleRate: 44100,
                sampleSize: 16
            } })
            .then((stream) => {
                mediaRecorder = new MediaRecorder(stream);

                mediaRecorder.ondataavailable = (e) => {
                    const formData = new FormData();
                    formData.append("file", e.data);

                    fetch("/blob", {
                        method: "POST",
                        body: formData
                    })
                    .catch((err) => {
                        console.error(err);
                    });
                };

                mediaRecorder.start(100);
                console.log("Record started");
            })
            .catch((err) => {
                console.error(`The following getUserMedia error occurred: ${err}`);
            });
    } else {
        console.log("getUserMedia not supported on your browser!");
    }
}

function stop_recording() {
    if (mediaRecorder !== null) {
        mediaRecorder.stop();
        mediaRecorder = null;
    }
    console.log("Record stopped");
}
