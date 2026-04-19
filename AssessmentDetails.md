Task Description: “Smart Drone Traffic Analyzer”
Your objective is to build a complete proof-of-concept application that analyzes drone video 
footage. The application must identify vehicles, track their movement, count them accurately, and 
export the findings into an automated report.
Expected User Workflow
1. Upload: A user opens the application and uploads a standard .mp4 drone video.
2. Processing: The system processes the video in the background, identifying and tracking 
vehicles (e.g., cars, trucks, buses) across frames.
3. Visualization: The user interface updates to display the processed video playback, 
showing active bounding boxes and unique tracking IDs on the vehicles.
4. Reporting: The interface presents a summary of the total unique vehicles counted and 
provides a button to download a generated CSV/Excel report containing the extracted 
data.
Technical Requirements
1. Front-End / User Interface Architecture
Building structured, production-ready interfaces is a core requirement. Rapid prototyping libraries 
such as Streamlit, Gradio, or Dash are strictly prohibited. You must choose one of the following 
paths:
 Web Application (Full-Stack Route)
Implement a decoupled architecture:
• Frontend: Use a modern framework (e.g., React, Vue, Next.js) or standard 
HTML/CSS/JS. Include loading states or progress indicators, as video processing takes 
time.
• Backend: Use a Python framework (e.g., FastAPI, Flask, Django).
• Communication: Handle file uploads and data streaming via REST APIs or  WebSockets.
Desktop Application (GUI Route)
• Use a comprehensive Python GUI framework (e.g., PyQt5, PyQt6, or PySide6).
• Requirement: Properly manage application state and concurrency (e.g., using QThread 
or worker threads) to ensure the UI remains responsive during processing. Handle basic 
UI error states (e.g., non-video file uploads).
2. Computer Vision Pipeline
• Process the uploaded video frame-by-frame. You may implement optimizations (like frame 
skipping or resizing) to improve processing speed without sacrificing accuracy.
• Utilize an off-the-shelf object detection model (e.g., YOLOv8, YOLOv10) capable of 
recognizing standard vehicle classes. No custom training is required.
3. Tracking and Logic
• Implement an object-tracking algorithm (e.g., DeepSORT, ByteTrack, or a custom logical 
implementation).
• The Core Challenge: Prevent double-counting. Your logic must accurately count unique 
vehicles passing through the scene, accounting for edge cases such as vehicles stopping, 
slowing down, or temporary occlusions (e.g., a car passing behind a lamppost).
4. Automation and Reporting
• The application must automatically generate a structured data report (CSV or Excel).
The report must include:
• Total vehicle count
• Breakdown by vehicle type
• Processing duration
• Frame and timestamp data for when vehicles  were detected
Provided Dataset
A sample drone video will be provided. Ensure your application is optimized to process this 
specific file, as it will act as our baseline for evaluation.
Data : Road Traffic - video Dataset
 we expect the final product to be significantly better, featuring a highly polished UI, 
flawless tracking logic, and comprehensive error handling.
Guidelines & Rules
• Strictly No Outsourcing: You must use your own intellect and engineering capabilities 
to architect and tackle these problems. You may not outsource this task, in part or in whole, 
to another person.
• AI Assistants  Allowed: I am fully permitted to use AI coding agents (e.g., Cursor, 
GitHub Copilot, ChatGPT, Claude). I am evaluating your architectural decisions, 
problem-solving, and integration skills, not your ability to write boilerplate.
• One-Time Instructions:  We want to assess how you work with initial requirements and 
make independent engineering decisions. While you may email us for critical, task￾breaking inquiries,  we expect you to work with what has been given. If a requirement 
seems ambiguous, make a reasonable engineering assumption and document it.
Deliverables
Please provide the following:
1. Source Code
A link to a Public GitHub Repository containing your project.
2. Thorough Documentation
A highly detailed README.md file. This must include:
• Step-by-step local setup instructions and dependency requirements.
• A breakdown of your chosen architecture (e.g., how the frontend communicates with the 
backend, or how threads are managed).
• An explanation of your tracking methodology and how you handled edge cases (like 
double-counting).
• Any engineering assumptions you made during development.

Evaluation Criteria
Criteria  Weight Focus Areas
Pipeline & Architecture 35% Frontend, backend/threads, CV model, 
reporting integration
Problem Solving & Logic 35% Tracking accuracy, edge cases, double￾counting prevention
Code Quality & Documentation 20% Readability, reproducibility, README 
thoroughness
User Experience 10% UI stability, loading states, overall usability