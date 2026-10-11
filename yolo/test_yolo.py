from ultralytics import YOLO
import cv2

model = YOLO("yolo26n-seg.pt")

cap = cv2.VideoCapture(1)

while True:
	ret, frame = cap.read()
	if not ret:
		break

	results = model(frame,device=0)
	annotated = results[0].plot()
	
	annotated = cv2.resize(annotated, (1280,720))
	cv2.imshow("YOLO", annotated)

	if cv2.waitKey(1) == ord('q'):
		break

cap.release()
cv2.destroyAllWindows()
