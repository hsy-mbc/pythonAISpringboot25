# post 요청을 통해 이미지가 전송되면 인공지능 객체 탐지 모델을 이용해서 객체를 탐지하고
# 그 결과 이미지를 base64 인코딩된 문자열로 반환하는 서비스를 구현
# 라이브러리 및 모듈 임포트
from idlelib.rpc import response_queue

# 관련 라이브러리 설치 터미널에서 진행
# pip install fastapi uvicorn pydantic Pillow numpy requests
# pip install ultralytics opencv-python python-multipart

# fastapi : 비동기 웹 프레임워크, 자동 OpenAPI 문서 생성
# uvicorn : 고성능 비동기 서버, ASGI 표준 지원
# pydantic : 데이터 검증, 직렬화, 타입 힌팅, 설정관리
# Pillow : 이미지 열기, 저장, 변환, 다양한 이미지 처리용
# numpy : 수치계산, 배열 및 행렬 연산, 다양한 수학함수
# requests : 간단한 http 요청 및 응답 처리
# ultralytics : YOLO8 객체 탐지 모델 제공
# opencv-python : 이미지 및 비디오 처리, 컴퓨터 비전 기능(roboflow 대체)
# python-multipart : 멀티파트 폼 데이터를 파싱하기 위함

# uvicorn main:app --reload 로 실행
from fastapi import FastAPI,UploadFile,File,Form  # 라우팅, 파일업로드, 폼 데이터 처리
                                                  # JSONResponse : json 응답 생성
from pydantic import BaseModel                    # pydantic의 데이터 모델을 정의
import io                                         # 파일 입출력을 위한 모듈
import base64                                     # 데이터를 Base64로 인코딩,디코딩
from PIL import Image                             # Pillow 이미지 처리 라이브러리
import numpy as np                                # 배열 및 행렬 연산을 위한 라이브러리
from starlette.requests import Request
from starlette.responses import Response
from ultralytics import YOLO                      # yolo8 모델 사용 울트라리틱스
import cv2                                        # 컴퓨터 비전 작업을 위한 라이브러리
from starlette.middleware.base import BaseHTTPMiddleware,RequestResponseEndpoint
import logging

app = FastAPI() # FastAPI() 객체를 생성한다

# ai 모델을 객체로 생성한다
model = YOLO('yolov8n.pt')
# YOLOv8 모델 로드 (yolo8n.pt 파일이 있어야 한다. 모델의 가중치 파일) 정답파일? 객체 탐지?

# 객체 탐지용 클래스 생성
# pydantic을 사용하여 데이터 모델을 정의 (응답 데이터를 구조화)
class DetectionResult(BaseModel):
    message : str  # 클라이언트가 보낸 메세지
    image : str    # Base64로 인코딩된 탐지 결과 이미지

# 객체 탐지 함수
# 객체 탐지를 위한 함수 정의로 모델에 이미지를 넣어 객체를 탐지하고
# 그 결과에서 바운딩 박스 정보를 추출한 후 이미지에
# 바인딩 박스와 클래스 이름, 신뢰도를 표시한 후 반환
def detect_object(image : Image):
    img = np.array(image)       # 이미지를 numpy 배열로 변환
    results = model(img)         # 객체 탐지
    class_names = model.names   # 클래스 이름 저장

    # 결과를 바운딩 박스, 클래스 이름, 정확도로 이미지에 표시
    for result in results:
        boxes = result.boxes.xyxy       # 바운딩 박스
        confidences = result.boxes.conf # 신뢰도
        class_ids = result.boxes.cls    # 클래스 이름

        for box, confidences, class_ids in zip(boxes,confidences,class_ids):
            x1,y1,x2,y2 = map(int,box) # 좌표를 점수로 반환
            label = class_names[int(class_ids)] # 클래스 이름
            cv2.rectangle(img, (x1,y1),(x2,y2),(255,0,0),2)
            cv2.putText(img,f'{label}{confidences:.2f}',
                        (x1,y1),cv2.FONT_HERSHEY_SIMPLEX,
                        0.9,(255,0,0),2)
    result_image = Image.fromarray(img) # 결과 이미지를 PIL로 변환
    return result_image
    # 결론 : YOLO 모델로 객체 탐지 수행
    # 탐지된 객체에 대해 바운딩 박스를 그리고 정확도 점수를 이미지에 표시
    # 결과 이미지를 PIL 이미지로 변환하여 반환

class LoggingMiddleware(BaseHTTPMiddleware): # 로그를 콘솔에 출력
    logging.basicConfig(level = logging.INFO) # 로그 출력 추가
    async def dispatch(self, request, call_next):
        logging.info(f"Req : {request.method}{request.url}")
        response = await call_next(request)
        logging.info(f"Status Code : {response.status_code}")
        return response
app.add_middleware(LoggingMiddleware)
# 모든 요청에 대해 로그를 남기게 미들웨어 클래스를 사용함

@app.get("/") # http://localhost:8000/
# async def read_root(): 기본 주소는 index로 많이들 한다~ index로 하자
async def index():
    return {"message":"Hello FastAPI"}

# http://localhost:8000/detect
@app.post("/detect",response_model=DetectionResult)
async def detect_service(message : str = Form(...), file:UploadFile = File(...)):
    # 이미지를 읽어서 PIL 이미지로 변환
    image = Image.open(io.BytesIO(await file.read()))

    # 알파 채널 제거하고 RGB로 변환
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    elif image.mode !='RGB':
        image = image.convert('RGB')

    # 객체 탐지 수행 -> 이미지가 들어가서 모델에서 처리 후 결과를 받음
    result_image = detect_object(image)

    # 이미지 결과를 base64로 인코딩
    buffered = io.BytesIO()
    result_image.save(buffered,format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return DetectionResult(message=message,image=img_str)
    # -> 스프링 부트로 JSON 처리
    # 결론 : /detect 경로에 post 요청 처리
    # 클라이언트에서 업로드된 이미지를 읽고 PIL 이미지로 변환,
    # 알파채널이 있으면 알파 채널을 제거
    # 객체 탐지 함수를 호출하여 탐지 결과 이미지를 얻는다
    # 탐지 결과 이미지를 Base64 문자열로 인코딩
    # DetectionResult 모델을 사용하여 메시지와 인코딩된 이미지를 json 응답으로 반환




if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=8000)
    # main.py를 실행할 때 포트번호를 기재해줌
    #  uvicorn main:app --reload 로 실행 ( 수정 후 재시작 ))
