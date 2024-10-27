import cv2
import numpy as np
import os
import speech_recognition as sr
import pyttsx3
from picamera2 import Picamera2
import time

# Initialize text-to-speech engine
engine = pyttsx3.init()

# Initialize the face recognizer and face detector for profile faces
recognizer = cv2.face.LBPHFaceRecognizer_create()
face_cascade = cv2.CascadeClassifier('haarcascade_profileface.xml')
frontal_face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
r = sr.Recognizer()

def speak(text):
    engine.say(text)
    engine.runAndWait()

def get_input_from_voice(prompt_text):
    with sr.Microphone() as source:
        speak(prompt_text)
        audio = r.listen(source)
    try:
        response = r.recognize_google(audio)
        speak(f"You said: {response}")
        return response
    except sr.UnknownValueError:
        speak("Could not understand audio")
        return None
    except sr.RequestError as e:
        speak(f"Could not request results; {e}")
        return None

def get_next_id():
    if not os.path.exists('names.txt'):
        return 1
    else:
        with open('names.txt', 'r') as f:
            lines = f.readlines()
            if not lines:
                return 1
            else:
                ids = [int(line.split(',')[0]) for line in lines]
                return max(ids) + 1

def save_name_and_phone(name, phone, id):
    with open('names.txt', 'a') as f:
        f.write(f"{id},{name},{phone}\n")

def capture_images(name, id):
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)}))
    picam2.start()

    sampleNum = 0
    angles_collected = {
        "frontal": False,
        "left_profile": False,
        "right_profile": False
    }

    while sampleNum < 20:  # Capture until 20 images are saved
        img = picam2.capture_array()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect frontal faces
        frontal_faces = frontal_face_cascade.detectMultiScale(gray, 1.3, 5)
        if len(frontal_faces) > 0 and not angles_collected["frontal"]:
            angles_collected["frontal"] = True
            speak("Frontal face detected.")

        # Detect left profile faces
        profile_faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        if len(profile_faces) > 0 and not angles_collected["left_profile"]:
            angles_collected["left_profile"] = True
            speak("Left profile face detected.")

        # Flip image to detect right profile (since the cascade is for left profile)
        flipped_img = cv2.flip(gray, 1)
        right_profile_faces = face_cascade.detectMultiScale(flipped_img, 1.3, 5)
        if len(right_profile_faces) > 0 and not angles_collected["right_profile"]:
            angles_collected["right_profile"] = True
            speak("Right profile face detected.")

        # Save images for each detected face (frontal and profile)
        for (x, y, w, h) in frontal_faces:
            sampleNum += 1
            cv2.imwrite(f"dataset/User.{id}.{sampleNum}.jpg", gray[y:y + h, x:x + w])
            cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)

        for (x, y, w, h) in profile_faces:
            sampleNum += 1
            cv2.imwrite(f"dataset/User.{id}.{sampleNum}.jpg", gray[y:y + h, x:x + w])
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

        for (x, y, w, h) in right_profile_faces:
            sampleNum += 1
            flipped_face = flipped_img[y:y + h, x:x + w]
            cv2.imwrite(f"dataset/User.{id}.{sampleNum}.jpg", cv2.flip(flipped_face, 1))
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2)

        # Display the image
        cv2.imshow('Capturing Images', img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        # Break if we have captured 20 images
        if sampleNum >= 20:
            break

        time.sleep(0.1)  # Short delay to prevent capturing too quickly

    picam2.stop()
    cv2.destroyAllWindows()

def get_images_and_labels(path):
    image_paths = [os.path.join(path, f) for f in os.listdir(path)]
    face_samples = []
    ids = []
    for imagePath in image_paths:
        img_numpy = cv2.imread(imagePath, cv2.IMREAD_GRAYSCALE)
        if img_numpy is None:
            continue
        id = int(os.path.split(imagePath)[-1].split(".")[1])
        faces = face_cascade.detectMultiScale(img_numpy)
        for (x, y, w, h) in faces:
            face_samples.append(img_numpy[y:y + h, x:x + w])
            ids.append(id)
    return face_samples, ids

def train_recognizer():
    faces, ids = get_images_and_labels('dataset')
    recognizer.train(faces, np.array(ids))
    recognizer.write('trainer/trainer.yml')

if __name__ == '__main__':
    if not os.path.exists('dataset'):
        os.makedirs('dataset')
    if not os.path.exists('trainer'):
        os.makedirs('trainer')
        
    name = get_input_from_voice("Please say the name of the person.")
    if name:
        phone = get_input_from_voice("Now, please say the phone number.")
        if phone:
            id = get_next_id()
            save_name_and_phone(name, phone, id)
            speak(f"Collecting images for {name}. Please look at the camera from different angles.")
            capture_images(name, id)
            speak("Training the recognizer. Please wait...")
            train_recognizer()
            speak("Training completed successfully.")
        else:
            speak("Phone number not provided. Exiting.")
    else:
        speak("Name not provided. Exiting.")
