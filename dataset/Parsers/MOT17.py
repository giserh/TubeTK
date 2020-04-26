import os
import os.path
import cv2
import numpy as np
import random
import pickle
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True


class GTSingleParser_MOT_17:
    def __init__(self, folder,
                 forward_frames=8,
                 frame_stride=1,
                 min_vis=-0.1,
                 value_range=1,
                 type='train'):
        self.type = type
        self.frame_stride = frame_stride
        self.value_range = value_range
        self.folder = folder

        self.min_vis = min_vis
        self.forward_frames = forward_frames
        self.max_frame_index = len(os.listdir(os.path.join(self.folder, 'img1'))) - (
                    self.forward_frames * 2 - 1) * self.frame_stride

        if frame_stride != -1:
            self.tube_folder = 'tubes_' + str(forward_frames) + '_' + str(frame_stride) + '_' + str(min_vis)

            if type == 'train':
                assert os.path.exists(os.path.join(self.folder, self.tube_folder)), 'Tube folder does not exist: ' + str(os.path.join(self.folder, self.tube_folder))

    def _getimage(self, frame_index):
        image_file = os.path.join(self.folder, 'img1/{0:06}.jpg'.format(frame_index + 1))
        # return cv2.imread(image_file)
        for i in range(10):
            try:
                assert os.path.exists(image_file), 'Image does not exist: {}'.format(image_file)
                img = cv2.cvtColor(np.asarray(Image.open(image_file).convert("RGB")), cv2.COLOR_RGB2BGR)
                break
            except:
                print('READ IMAGE ERROR: ' + str(image_file))
                print("IMAGE EXIST: " + str(os.path.exists(image_file)))
        return img

    def get_item(self, frame_index):
        if self.frame_stride == -1:
            strides = [1,2,4]
            frame_stride = strides[random.randint(0, 2)]
            self.tube_folder = 'tubes_' + str(self.forward_frames) + '_' + str(frame_stride) + '_' + str(self.min_vis)
            if type == 'train':
                assert os.path.exists(
                    os.path.join(self.folder, self.tube_folder)), 'Tube folder does not exist: ' + str(
                    os.path.join(self.folder, self.tube_folder))
        else:
            frame_stride = self.frame_stride

        start_frame = frame_index
        max_len = self.forward_frames * 2 * frame_stride
        tube_file = os.path.join(self.folder, self.tube_folder, str(start_frame))
        if self.type == 'train':
            if not os.path.exists(tube_file):
                print(tube_file)
                return None, None, None, None, None

        # get image meta
        img_meta = {}
        image = self._getimage(frame_index)
        if image is None:
            print(os.path.join(self.folder, 'img1/{0:06}.jpg'.format(frame_index + 1)))
        img_meta['img_shape'] = [max_len, image.shape[0], image.shape[1]]
        img_meta['value_range'] = self.value_range
        img_meta['pad_percent'] = [1, 1]  # prepared for padding
        img_meta['video_name'] = os.path.basename(self.folder)
        img_meta['start_frame'] = start_frame

        # get image
        imgs = []
        for i in range(self.forward_frames * 2):
            frame_index = start_frame + i * frame_stride
            image = self._getimage(frame_index)  # h, w, c
            imgs.append(image)

        # get_tube
        tubes = np.zeros((1, 15))
        if self.type == 'train':
            tubes = pickle.load(open(tube_file, 'rb'))

        num_dets = len(tubes)
        labels = np.ones((num_dets, 1))  # only human class

        tubes = np.array(tubes)
        imgs = np.array(imgs)

        return imgs, img_meta, tubes, labels, start_frame

    def __len__(self):
        return self.max_frame_index


class GTParser_MOT_17:
    def __init__(self, mot_root,
                 type='train',
                 test_seq=None,
                 forward_frames=4,
                 frame_stride=1,
                 min_vis=-0.1,
                 value_range=1):
        # analsis all the folder in mot_root
        # 1. get all the folders
        mot_root = os.path.join(mot_root, type)
        if test_seq is None:
            all_folders = sorted(
                [os.path.join(mot_root, i) for i in os.listdir(mot_root)
                 if os.path.isdir(os.path.join(mot_root, i))
                 and i.find('FRCNN') != -1]
            )
        else:
            all_folders = sorted(
                [os.path.join(mot_root, i) for i in os.listdir(mot_root)
                 if os.path.isdir(os.path.join(mot_root, i))
                 and i.find('FRCNN') != -1
                 and i in test_seq]
            )
        # 2. create single parser
        self.parsers = [GTSingleParser_MOT_17(folder, forward_frames=forward_frames, frame_stride=frame_stride,
                                              min_vis=min_vis, value_range=value_range, type=type) for folder in all_folders]

        # 3. get some basic information
        self.lens = [len(p) for p in self.parsers]
        self.len = sum(self.lens)

    def __len__(self):
        # get the length of all the matching frame
        return self.len

    def __getitem__(self, item):
        # 1. find the parser
        total_len = 0
        index = 0
        current_item = item
        for l in self.lens:
            total_len += l
            if item < total_len:
                break
            else:
                index += 1
                current_item -= l

        # 2. get items
        if index >= len(self.parsers):
            return None, None, None, None, None
        return self.parsers[index].get_item(current_item)
