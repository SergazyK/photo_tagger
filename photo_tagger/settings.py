descriptor_size = 512
strong_verification_threshold = 1
weak_verification_treshold = 1.24

# Face detection and recognition
recognition_model_path = 'vision/models'
ssh_model_path = 'vision/SSH/model/'
mtcnn_model_path = 'vision/mtcnn-model/'
scales = [1200, 1600]
detection_threshold = 0.5

#telegram
token = ''

#TODO
texts = {
    'hello': 'Hi! I am photo sharing bot. Please send me your selfie to retrieve your photos. Then you can send and receive photos.',
    'bad_selfie': '',
    'auth_failed': '',
    'accepted_selfie': ''
}