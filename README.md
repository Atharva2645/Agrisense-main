# 🌱 AgriSense AI – AI-Based Produce Quality Grading & District-Level Market Intelligence System

**AgriSense AI** is an AI-powered agricultural web application designed to help farmers and produce sellers assess the quality of fruits and vegetables and make better selling decisions using district-level market intelligence.

The system uses Artificial Intelligence, Deep Learning, and Computer Vision to identify agricultural produce, analyze visible defects, predict quality grades, estimate shelf life, and provide grade-wise market price information.

It also compares APMC market prices across different districts and recommends potentially better markets based on expected selling value and applicable costs.

## 🚀 Live Demo

🌐 **Live Application:** https://agrisense-ai-main.vercel.app/

💻 **GitHub Repository:** https://github.com/Atharva2645/Agrisense-main

## ✨ Key Features

### 1. AI-Based Produce Identification
- Identifies supported fruits and vegetables from uploaded images.
- Uses CNN-based deep learning models and transfer learning.
- Provides prediction confidence scores.

### 2. Intelligent Quality Grading
- Analyzes visible characteristics such as colour, freshness, spots, bruises, shape, and surface defects.
- Calculates an overall quality score.
- Classifies agricultural produce into three quality grades:

| Grade | Quality |
|---|---|
| Grade A | High Quality |
| Grade B | Medium Quality |
| Grade C | Low Quality |

### 3. Image Validation
- Validates uploaded images before AI processing.
- Rejects invalid, unclear, blurry, or unsupported images.
- Displays appropriate error messages to prevent unreliable predictions.

### 4. Shelf-Life Estimation
- Estimates the expected remaining shelf life of agricultural produce.
- Provides indicative nutritional-loss information based on produce condition and quality grade.

### 5. Grade-Wise Market Price Estimation
- Uses minimum, modal, and maximum prices from the selected APMC market.
- Calculates separate expected prices for Grade A, Grade B, and Grade C produce.
- Displays estimated price ranges to help users understand the market value of their produce.

### 6. District-Level Market Intelligence
- Compares agricultural market prices across different districts and APMC markets.
- Considers expected selling prices, transportation costs, and other applicable expenses.
- Recommends potentially better markets based on estimated net selling value.

### 7. User Authentication & Analysis History
- Provides user registration and login functionality.
- Maintains individual user analysis records.
- Allows users to access previous produce quality assessments.

### 8. Responsive Dashboard
- Interactive and user-friendly interface.
- Supports image uploading and camera capture.
- Accessible through desktop and mobile browsers.

## 🛠️ Technology Stack

| Category | Technologies |
|---|---|
| Frontend | React.js, JavaScript |
| Styling | Tailwind CSS |
| HTTP Requests | Axios |
| Backend | Node.js, Express.js |
| AI/ML | Python, PyTorch, TorchVision |
| Deep Learning | CNN, EfficientNet-B0, Transfer Learning |
| Image Processing | OpenCV, NumPy |
| Database | MongoDB |
| Model Development | Jupyter Notebook, Hugging Face |
| Development Tools | VS Code, Git, GitHub |

## 🏗️ System Architecture

AgriSense AI follows a three-layer architecture:

**1. Frontend Layer**
- Developed using React.js.
- Handles user authentication, image uploading, camera capture, district selection, and result visualization.
- Displays quality assessment results and market recommendations.

**2. Backend and AI Processing Layer**
- Handles API requests and image validation.
- Performs image preprocessing and feature extraction.
- Uses deep learning models for produce identification and quality analysis.
- Calculates quality scores, grades, shelf life, and nutritional-loss estimates.

**3. Data Storage and Output Layer**
- Uses MongoDB to manage user information and analysis history.
- Stores produce assessment records and market-related information.
- Provides APMC market prices and cost information for market comparisons.

## 🔄 Application Workflow

1. User registers or logs into the application.
2. User uploads an image or captures a photograph of agricultural produce.
3. The system validates the uploaded image.
4. OpenCV preprocesses the image through resizing, colour conversion, and normalization.
5. The trained AI model identifies the fruit or vegetable.
6. The system analyzes visible quality characteristics and defects.
7. A quality score is calculated and the produce is classified into Grade A, B, or C.
8. The system estimates shelf life and nutritional loss.
9. Grade-wise market prices are calculated using APMC market rates.
10. District-wise market comparisons are performed.
11. The system recommends a potentially better market based on estimated net selling value.
12. The final results are displayed on the dashboard and saved in analysis history.

## 📊 Market Price Calculation

The system uses minimum, modal, and maximum APMC market prices to calculate expected prices for different quality grades.

- **Grade A:** Higher expected price based on the market's price range.
- **Grade B:** Intermediate expected price.
- **Grade C:** Lower expected price.

Market recommendations consider the estimated selling value after applicable transportation and other costs.

**Estimated Net Selling Value:**

`Net Value = Expected Selling Price - Transportation Cost - Other Costs`

## 💻 Installation and Setup

### Prerequisites

Make sure the following tools are installed:

- Node.js and npm
- Python 3.x
- MongoDB
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/Atharva2645/Agrisense-main.git
```

### 2. Navigate to the Project Directory

```bash
cd Agrisense-main
```

### 3. Install Frontend and Backend Dependencies

Navigate to the respective frontend and backend directories and install their dependencies:

```bash
npm install
```

### 4. Set Up Python Environment

Create and activate a virtual environment:

```bash
python -m venv .venv
```

For Windows:

```bash
.venv\Scripts\activate
```

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create the required `.env` file in the appropriate backend directory and configure database connections, authentication secrets, API URLs, and other required settings.

### 6. Run the Application

Start the frontend and backend using their respective development scripts.

Start the Python AI processing service separately if your project configuration uses a separate AI service.

**Note:** The exact directory names, environment variables, and startup commands depend on the repository's current configuration.

## 🎯 Project Objectives

- Automate preliminary agricultural produce quality assessment.
- Reduce dependency on traditional manual inspection.
- Identify supported fruits and vegetables using AI.
- Provide consistent quality grading through computer vision.
- Estimate grade-wise agricultural market prices.
- Help farmers compare district-level APMC markets.
- Support better selling and storage decisions through data-driven insights.

## 🔮 Future Enhancements

- Support additional fruit and vegetable categories.
- Improve AI model performance using larger and more diverse datasets.
- Integrate real-time APMC market price information.
- Improve market recommendations using more accurate transportation and selling expenses.
- Develop dedicated Android and iOS applications.
- Introduce multilingual support for regional languages.
- Expand agricultural market intelligence capabilities.

## 👨‍💻 Project Team

**Project Group:** G55  
**Department:** Computer Science and Engineering  
**College:** D. Y. Patil College of Engineering and Technology, Kolhapur  
**Academic Year:** 2026–2027

| Team Member | Primary Contribution |
|---|---|
| Sahil Padavale | Research and Documentation |
| Prachi Chougale | UI and Frontend Development |
| Atharv Bhasme | AI/ML Model, Image Processing, Produce Classification and Quality Scoring |
| Yash Sankpal | Backend Development, APIs and Database Integration |
| Harshad Bhalekar | Dataset Collection and Market Data |

**Project Guide:** Mrs. V. P. Patil

## ⚠️ Disclaimer

AgriSense AI provides preliminary produce quality assessments and indicative market price, shelf-life, and nutritional-loss estimates.

Actual produce quality, market prices, shelf life, and nutritional conditions may vary depending on geographical location, storage conditions, market demand, supply, and other environmental factors.

The system is intended to support agricultural decision-making and should not replace professional inspection or verified market information.

## ⭐ Support

If you find this project useful, consider giving the repository a ⭐ on GitHub.

---

**AgriSense AI – Smart Quality Assessment. Better Market Decisions. Smarter Agriculture.** 🌱
