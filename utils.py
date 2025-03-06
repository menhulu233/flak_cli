#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   @File Name:     utils.py
   @Description:
-------------------------------------------------
"""
import warnings
warnings.filterwarnings('ignore')
from ultralytics import YOLO
import streamlit as st
import cv2
from PIL import Image
# import tempfile
import pandas as pd
import time
import config
# import fileinput
# import numpy as np

saved_dir = config.saved_dir

def folder_name():
    folder_name = time.strftime('%Y-%m-%d-%H-%M-%S')
    return str(folder_name)


def transform_predict_to_df(results: list, labeles_dict: dict) -> pd.DataFrame:
    """
    Transform predict from yolov8 (torch.Tensor) to pandas DataFrame.

    Args:
        results (list): A list containing the predict output from yolov8 in the form of a torch.Tensor.
        labeles_dict (dict): A dictionary containing the labels names, where the keys are the class ids and the values are the label names.
        
    Returns:
        predict_bbox (pd.DataFrame): A DataFrame containing the bounding box coordinates, confidence scores and class labels.
    """
    # Transform the Tensor to numpy array
    predict_bbox = pd.DataFrame(results[0].to("cpu").numpy().boxes.xyxy, columns=['xmin', 'ymin', 'xmax','ymax'])
    # Add the confidence of the prediction to the DataFrame
    predict_bbox['confidence'] = results[0].to("cpu").numpy().boxes.conf
    # Add the class of the prediction to the DataFrame
    predict_bbox['class'] = (results[0].to("cpu").numpy().boxes.cls).astype(int)
    # Replace the class number with the class name from the labeles_dict
    predict_bbox['name'] = predict_bbox["class"].replace(labeles_dict)
    return predict_bbox


def transform_video_frame_predict_to_df(results: list, labeles_dict: dict, video_name: str) -> pd.DataFrame:
    """
    Transform predict from yolov8 (torch.Tensor) to pandas DataFrame.

    Args:
        results (list): A list containing the predict output from yolov8 in the form of a torch.Tensor.
        labeles_dict (dict): A dictionary containing the labels names, where the keys are the class ids and the values are the label names.
        
    Returns:
        predict_bbox (pd.DataFrame): A DataFrame containing the bounding box coordinates, confidence scores and class labels.
    """
    # Transform the Tensor to numpy array
    predict_bbox = pd.DataFrame(results[0].to("cpu").numpy().boxes.xyxy, columns=['xmin', 'ymin', 'xmax','ymax'])
    # Add the confidence of the prediction to the DataFrame
    predict_bbox['confidence'] = results[0].to("cpu").numpy().boxes.conf
    # Add the class of the prediction to the DataFrame
    predict_bbox['class'] = (results[0].to("cpu").numpy().boxes.cls).astype(int)
    # Replace the class number with the class name from the labeles_dict
    predict_bbox['name'] = predict_bbox["class"].replace(labeles_dict)
    predict_bbox['video_name'] = video_name
    return predict_bbox


def _display_detected_frames(conf, model, st_frame, image, iou_thre):
    """
    Display the detected objects on a video frame using the YOLOv8 model.
    :param conf (float): Confidence threshold for object detection.
    :param model (YOLOv8): An instance of the `YOLOv8` class containing the YOLOv8 model.
    :param st_frame (Streamlit object): A Streamlit object to display the detected video.
    :param image (numpy array): A numpy array representing the video frame.
    :return: None
    """
    # Resize the image to a standard size
    # image = cv2.resize(image, (720, int(720 * (9 / 16))))

    # Predict the objects in the image using YOLOv8 model
    res = model.predict(image, conf=conf, iou=iou_thre)
    
    # Plot the detected objects on the video frame
    res_plotted = res[0].plot()

    # speed
    inference_time = round(res[0].speed['preprocess'] + res[0].speed['inference'] + res[0].speed['postprocess'], 2)
    
    st_frame.image(res_plotted,
                   caption='Detected Video',
                   channels="BGR",
                   use_column_width=True
                   )
    
    return inference_time, res_plotted, res


@st.cache_resource
def load_model(model_path, device):
    """
    Loads a YOLO object detection model from the specified model_path.

    Parameters:
        model_path (str): The path to the YOLO model file.

    Returns:
        A YOLO object detection model.
    """
    model = YOLO(model_path, device)
    return model


def infer_uploaded_image(conf, model, save_flag=False, iou_thre=0.45):
    """
    Execute inference for uploaded image
    :param conf: Confidence of YOLOv8 model
    :param model: An instance of the `YOLOv8` class containing the YOLOv8 model.
    :return: None
    """
    source_img = st.sidebar.file_uploader(
        label="Choose an image...",
        type=("jpg", "jpeg", "png", 'bmp', 'webp')
    )

    inference_time, obj_nums, image_height, image_width = '', '', '', ''
    st1, st2, st3, st4 = st.columns(4)
    with st1:
        st.markdown("### 图像检测用时")
        st1_text = st.markdown(f"{inference_time}")
    with st2:
        st.markdown("### 检测目标总数")
        st2_text = st.markdown(f"{obj_nums}")
    with st3:
        st.markdown("### 图像宽度")
        st3_text = st.markdown(f"{image_width}")
    with st4:
        st.markdown("### 图像高度")
        st4_text = st.markdown(f"{image_height}")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        if source_img:
            uploaded_image = Image.open(source_img)
            # adding the uploaded image to the page with caption
            st.image(
                image=source_img,
                caption="Uploaded Image",
                use_column_width=True
            )
           
    if source_img:
        if st.button("开始检测"):
            with st.spinner("正在运行..."):
                uploaded_image.save(str(config.saved_file_path) + '/' + folder_name() + '-' + source_img.name)
                res = model.predict(uploaded_image,
                                    conf=conf,
                                    iou=iou_thre)
                boxes = res[0].boxes
                res_plotted = res[0].plot()[:, :, ::-1]

                with col2:
                    st.image(res_plotted,
                             caption="Detected Image",
                             use_column_width=True)
                    try:
                        with st.expander("Detection Results"):
                            predicted = transform_predict_to_df(res, model.model.names)
                            st.dataframe(predicted)
                    except Exception as ex:
                        st.write("No image is uploaded yet!")
                        st.write(ex)

                # speed
                inference_time = round(res[0].speed['preprocess'] + res[0].speed['inference'] + res[0].speed['postprocess'], 2)
                image_height, image_width = res[0].orig_shape
                st1_text.markdown(f"### {str(inference_time) + 'ms'}")
                st2_text.markdown(f"### {res[0].boxes.cls.shape[0]}")
                st3_text.markdown(f"### {image_width}")
                st4_text.markdown(f"### {image_height}")

                if save_flag:
                    folder = folder_name()
                    cv2.imwrite(str(saved_dir) + '/' + folder + '-' + source_img.name, res_plotted[:, :, ::-1])
                
                st.markdown("---")
                # st1, st2 = st.columns(2)
                st5 = st.empty()
                predicted = transform_predict_to_df(res, model.model.names)
                st5.markdown("##### " + source_img.name)
                st6 = st.empty()
                st6.dataframe(predicted, use_container_width=True)

                # chart_data = pd.DataFrame(predicted, columns=["name"])
                # st2.bar_chart(chart_data)
                #          xmin        ymin         xmax        ymax  confidence  class    name
                # 0  124.999146  198.131470  1110.519287  710.520081    0.813643      0  person
                # 1  747.740112   42.012146  1137.684326  714.162659    0.796988      0  person
                # 2  436.749023  437.312622   523.376465  713.892700    0.401118     27     tie
                # inference_time, obj_nums, image_height, image_width = '', '', '', ''
                # st1, st2, st3, st4 = st.columns(4)
                # with st1:
                #     st.markdown("### 图像检测用时")
                #     st1_text = st.markdown(f"{inference_time}")
                # with st2:
                #     st.markdown("### 检测目标总数")
                #     st2_text = st.markdown(f"{obj_nums}")
                # with st3:
                #     st.markdown("### 图像宽度")
                #     st3_text = st.markdown(f"{image_width}")
                # with st4:
                #     st.markdown("### 图像高度")
                #     st4_text = st.markdown(f"{image_height}")

                # st.markdown("---")


def infer_uploaded_video(conf, model, save_flag=False, iou_thre=0.45):
    """
    Execute inference for uploaded video
    :param conf: Confidence of YOLOv8 model
    :param model: An instance of the `YOLOv8` class containing the YOLOv8 model.
    :return: None
    """
    source_video = st.sidebar.file_uploader(
        label="Choose a video...",
        type=("mp4", "avi", "gif", 'tiff', 'mov')
    )   

    inference_time, fps, height, width = '', '', '', ''
    st1, st2, st3, st4 = st.columns(4)
    with st1:
        st.markdown("### 推理时间")
        st1_text = st.markdown(f"{inference_time}")
    with st2:
        st.markdown("### 检测速度(FPS)")
        st2_text = st.markdown(f"{fps}")
    with st3:
        st.markdown("### 视频宽度")
        st3_text = st.markdown(f"{width}")
    with st4:
        st.markdown("### 视频高度")
        st4_text = st.markdown(f"{height}")

    st.markdown("---")

    col1, col2 = st.columns(2)
    
    # 源视频
    with col1:
        if source_video:
            st.video(source_video)

    # 配置参数
    pd_result = None
    frame_i = 0

    if source_video:       
        if st.button("开始检测"):
            with st.spinner("正在运行..."):
                # 保存源视频
                vid_file = str(config.saved_file_path) + '/' + folder_name() + '-' + source_video.name
                with open(vid_file, 'wb') as out:
                    out.write(source_video.read())
                try:
                    vid_cap = cv2.VideoCapture(
                        vid_file)
                    frame_width = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))  
                    frame_height = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    frame_rate = int(vid_cap.get(cv2.CAP_PROP_FPS)) 
                    st3_text.markdown(f"### {frame_width}")
                    st4_text.markdown(f"### {frame_height}")

                    if save_flag:
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        writer_out = cv2.VideoWriter(str(saved_dir) + '/' + folder_name() + '-prediction.mp4', fourcc, frame_rate, (frame_width, frame_height))

                    with col2:
                        st_frame = st.empty()
                    while (vid_cap.isOpened()):
                        with col2:
                            success, image = vid_cap.read()
                            if success:
                                inference_time, res_plotted, res = _display_detected_frames(conf,
                                                        model,
                                                        st_frame,
                                                        image,
                                                        iou_thre
                                                        )
                                fps = round(1000 / inference_time, 2)
                                st1_text.markdown(f"### {str(inference_time) + ' ms'}")
                                st2_text.markdown(f"### {fps}")
                                frame_i += 1

                                # 合并检测结果
                                predicted = transform_video_frame_predict_to_df(res, model.model.names, source_video.name + '_frame_' + str(frame_i))
                                pd_result = pd.concat([pd_result, predicted], axis=0)

                                # write result
                                if save_flag:
                                    writer_out.write(res_plotted)

                            else:
                                vid_cap.release()
                                writer_out.release()
                                break
                        
                except Exception as e:
                    st.error(f"Error loading video: {e}")
    
        st.markdown("---")
        st8 = st.empty()
        st8.markdown("##### " + source_video.name)
        st9 = st.empty()
        st9.dataframe(pd_result, use_container_width=True)


def infer_uploaded_webcam(conf, model, save_flag=False, iou_thre=0.45):
    """
    Execute inference for webcam.
    :param conf: Confidence of YOLOv8 model
    :param model: An instance of the `YOLOv8` class containing the YOLOv8 model.
    :return: None
    """
    frame_ii = 0
    inference_time, fps, height, width = '', '', '', ''
    st1, st2, st3, st4 = st.columns(4)
    with st1:
        st.markdown("### 推理时间")
        st1_text = st.markdown(f"{inference_time}")
    with st2:
        st.markdown("### 检测速度(FPS)")
        st2_text = st.markdown(f"{fps}")
    with st3:
        st.markdown("### 视频宽度")
        st3_text = st.markdown(f"{width}")
    with st4:
        st.markdown("### 视频高度")
        st4_text = st.markdown(f"{height}")

    st.markdown("---")

    col1, col2 = st.columns(2)

    flag = st.button(
            label="结束检测"
        )

    try:
        camera_cap = cv2.VideoCapture(0)  # local camera
        frame_width = int(camera_cap.get(cv2.CAP_PROP_FRAME_WIDTH))  
        frame_height = int(camera_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        # frame_rate = int(camera_cap.get(cv2.CAP_PROP_FPS)) 
    except Exception as e:
        st.error(f"Error loading Camera: {str(e)}")
     
    st3_text.markdown(f"### {frame_width}")
    st4_text.markdown(f"### {frame_height}")

    if save_flag and not flag:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer_out = cv2.VideoWriter(str(saved_dir) + '/' + folder_name() + '-prediction_camera_detected.mp4', fourcc, 25.0, (frame_width, frame_height))
        writer_out_camera = cv2.VideoWriter(str(config.saved_file_path) + '/' + folder_name() + '-prediction_camera.mp4', fourcc, 25.0, (frame_width, frame_height))

    with col1:
        st_frame = st.empty()

    with col2:
        st_frame_detect = st.empty()

    while not flag:
        success, image = camera_cap.read()
        if success:
            writer_out_camera.write(image)
            st_frame.image(image,
                            caption='Camera image',
                channels="BGR",
                use_column_width=True)
            
            inference_time, res_plotted, res = _display_detected_frames(
                conf,
                model,
                st_frame_detect,
                image,
                iou_thre
            )
            fps = round(1000 / inference_time, 2)
            st1_text.markdown(f"### {str(inference_time) + ' ms'}")
            st2_text.markdown(f"### {fps}")
            frame_ii += 1

            # write result
            if save_flag:
                writer_out.write(res_plotted)
                
        else:
            camera_cap.release()
            writer_out.release()
            writer_out_camera.release()
            break
    

    
