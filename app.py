from sys import stdout
from makeup_artist import Makeup_artist
import logging
from flask import Flask, render_template, Response, request, jsonify
from flask_socketio import SocketIO
from camera import Camera
import binascii
from utils import base64_to_pil_image, pil_image_to_base64
import pickle
import numpy as np
import mediapipe as mp
import cv2
# import jsonify
import base64
from PIL import Image
import cv2
from io import StringIO
from io import BytesIO
import numpy as np
import time
#----------------- Video Transmission ------------------------------#
app = Flask(__name__)
app.logger.addHandler(logging.StreamHandler(stdout))
app.config['DEBUG'] = True
socketio = SocketIO(app)
camera = Camera(Makeup_artist())
model = loaded_model = pickle.load(open('random1200.pkl', 'rb'))
#model = keras.models.load_model('actionpro1.h5',compile = False)
#actions = np.array(['hello','bye','thanks', 'please','namaste','yes','no'])
actions = np.array(['thanks', 'please','namaste'])
#model = keras.models.load_model('action (1).h5',compile = False)
#actions = np.array(['hello', 'thanks', 'iloveyou'])
label_map = {label:num for num, label in enumerate(actions)}
# Thirty videos worth of data
no_sequences = 30

# Videos are going to be 30 frames in length
sequence_length = 30
mp_holistic = mp.solutions.holistic # Holistic model
mp_drawing = mp.solutions.drawing_utils # Drawing utilities

#---------------- Video Transmission --------------------------------#


#---------------- Video Socket Connections --------------------------#
@socketio.on('input image', namespace='/test')
def test_message(input):
    input = input.split(",")[1]
    camera.enqueue_input(input)
    #camera.enqueue_input(base64_to_pil_image(input))


@socketio.on('connect', namespace='/test')
def test_connect():
    app.logger.info("client connected")


@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')
def mediapipe_detection(image, model):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) # COLOR CONVERSION BGR 2 RGB
    image.flags.writeable = False                  # Image is no longer writeable
    results = model.process(image)                 # Make prediction
    image.flags.writeable = True                   # Image is now writeable 
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) # COLOR COVERSION RGB 2 BGR
    return image, results
def draw_landmarks(image, results):
    mp_drawing.draw_landmarks(image, results.face_landmarks, mp_holistic.FACE_CONNECTIONS) # Draw face connections
    mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS) # Draw pose connections
    mp_drawing.draw_landmarks(image, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS) # Draw left hand connections
    mp_drawing.draw_landmarks(image, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS) # Draw right hand connections

def draw_styled_landmarks(image, results):
    # Draw face connections
    mp_drawing.draw_landmarks(image, results.face_landmarks, mp_holistic.FACE_CONNECTIONS, 
                             mp_drawing.DrawingSpec(color=(80,110,10), thickness=1, circle_radius=1), 
                             mp_drawing.DrawingSpec(color=(80,256,121), thickness=1, circle_radius=1)
                             ) 
    # Draw pose connections
    mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS,
                             mp_drawing.DrawingSpec(color=(80,22,10), thickness=2, circle_radius=4), 
                             mp_drawing.DrawingSpec(color=(80,44,121), thickness=2, circle_radius=2)
                             ) 
    # Draw left hand connections
    mp_drawing.draw_landmarks(image, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS, 
                             mp_drawing.DrawingSpec(color=(121,22,76), thickness=2, circle_radius=4), 
                             mp_drawing.DrawingSpec(color=(121,44,250), thickness=2, circle_radius=2)
                             ) 
    # Draw right hand connections  
    mp_drawing.draw_landmarks(image, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS, 
                             mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=4), 
                             mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
                             ) 
def extract_keypoints(results):
    pose = np.array([[res.x, res.y, res.z, res.visibility] for res in results.pose_landmarks.landmark]).flatten() if results.pose_landmarks else np.zeros(33*4)
    face = np.array([[res.x, res.y, res.z] for res in results.face_landmarks.landmark]).flatten() if results.face_landmarks else np.zeros(468*3)
    lh = np.array([[res.x, res.y, res.z] for res in results.left_hand_landmarks.landmark]).flatten() if results.left_hand_landmarks else np.zeros(21*3)
    rh = np.array([[res.x, res.y, res.z] for res in results.right_hand_landmarks.landmark]).flatten() if results.right_hand_landmarks else np.zeros(21*3)
    return np.concatenate([pose, face, lh, rh])

colors = [(245,117,16), (117,245,16), (16,117,245),(245,117,16), (117,245,16), (16,117,245),(16,117,245)]
#colors = [(245,117,16), (117,245,16), (16,117,245)]
def prob_viz(res, actions, input_frame, colors):
    output_frame = input_frame.copy()
    for num, prob in enumerate(res):
        cv2.rectangle(output_frame, (0,60+num*40), (int(prob*100), 90+num*40), colors[num], -1)
        cv2.putText(output_frame, actions[num], (0, 85+num*40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2, cv2.LINE_AA)
        
    return output_frame



def readb64(base64_string):
    #sbuf = StringIO(base64_string)
    #sbuf.write(base64.b64decode(base64_string))
    #sbuf = sbuf.read().encode('utf8')
    #sbuf.write(base64_string)
    sbuf = BytesIO(base64_string)
    pimg = Image.open(sbuf)
    return cv2.cvtColor(np.array(pimg), cv2.COLOR_RGB2BGR)


  
def gen():
  print("in gen")
  sequence = []
  sentence = []
  threshold = 0.6

  
  # Set mediapipe model 
  with mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
      frame_rate = 24
      prev = 0
      while True:
          time_elapsed = time.time() - prev           

          # Read feed
          #ret, frame = cap.read()
          
          #print(frame)  
          print('////////////////////////')
          #frame = base64.b64encode(frame).decode('ascii')
          
          if time_elapsed > 1./frame_rate:
              frame = camera.get_frame()
                
                
              prev = time.time()
              frame = readb64(frame)
              #frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
              print(frame.shape) 
              frame = cv2.resize(frame,(640,480))  

              print(frame.shape)


              #frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  
              # Make detections
              image, results = mediapipe_detection(frame, holistic)

              # Draw landmarks
              draw_styled_landmarks(image, results)

              # 2. Prediction logic
              keypoints = extract_keypoints(results)

              sequence.append(keypoints)
              sequence = sequence[-30:]

              if len(sequence) == 30:

                  res = model.predict_proba(np.array(sequence).reshape(1, (np.array(sequence).shape[0]*np.array(sequence).shape[1])))[0]
                  print(actions[np.argmax(res)])


              #3. Viz logic
                  if (res[0] > 0.5) or (res[1] > 0.96) or (res[2] > 0.6) :  
                      if len(sentence) > 0: 
                          if actions[np.argmax(res)] != sentence[-1]:
                              sentence.append(actions[np.argmax(res)])
                      else:
                          sentence.append(actions[np.argmax(res)])

                  if len(sentence) > 5: 
                      sentence = sentence[-5:]

                  # Viz probabilities
                  image = prob_viz(res, actions, image, colors)

              cv2.rectangle(image, (0,0), (640, 40), (245, 117, 16), -1)
              cv2.putText(image, ' '.join(sentence), (3,30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

              # Show to screen
              #cv2.imshow('open_image',image)
              ret, buffer = cv2.imencode('.jpg', image)
              frame = buffer.tobytes()
              yield (b'--frame\r\n'
                     b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')       


def gen1():
    """Video streaming generator function."""

    app.logger.info("starting to generate frames!")
    while True:
        frame = camera.get_frame() #pil_image_to_base64(camera.get_frame())
        print(frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    socketio.run(app)
