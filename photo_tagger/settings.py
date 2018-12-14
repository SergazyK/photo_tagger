descriptor_size = 512
strong_verification_threshold = 1.14
weak_verification_treshold = 1.24

# Face detection and recognition
recognition_model_path = 'vision/models/model-r100-ii/model'
ssh_model_path = 'vision/SSH/model/e2ef'
mtcnn_model_path = 'vision/mtcnn-model/'
scales = [1200, 1600]
detection_threshold = 0.5

#telegram
token = '746055313:AAGFOGcegCc-xXlJJnb28zUbA8wD9cRSE-0'

#TODO
texts = {
    'hello': 'Hello! I am photo sharing bot. Please send me your selfie to retrieve your photos. Then you can send and receive photos.',
    'bad_selfie': 'Seems like there is no person on photo, please make photo of only yourself',
    'auth_failed': 'Seems like you already registerd before, contact admin to delete other account',
    'accepted_selfie': 'Cheers! Now you can send photos and receive them. Just send me photos with your friends, and I will tag them'
}