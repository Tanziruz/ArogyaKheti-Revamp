import requests
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

fertilizerdata = pd.read_csv("datasets/Fertilizer Prediction.csv") 
openweather_api_key = os.environ.get('OPENWEATHER_API_KEY')
govdata_api_key = os.environ.get('GOVDATA_API_KEY')

def getWeatherDetails(coords):
    lat, lon = coords
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        print("⚠️ OpenWeather API key not found in .env")
        return "Unknown", 0, 0, 0, 0

    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()

        weather = data["weather"][0]["main"]
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]
        pressure = data["main"]["pressure"]

        return weather, temp, humidity, wind_speed, pressure

    except requests.RequestException as e:
        print(f"❌ Network error in getWeatherDetails: {e}")
        return "Unknown", 0, 0, 0, 0
    except KeyError as e:
        print(f"❌ Invalid API response format: {e}")
        return "Unknown", 0, 0, 0, 0
    except Exception as e:
        print(f"❌ Unexpected error in getWeatherDetails: {e}")
        return "Unknown", 0, 0, 0, 0

def getAgroNews():
    api_key = os.environ.get("WORLDNEWS_API_KEY")
    if not api_key:
        print("WORLDNEWS_API_KEY not found in .env")
        return []

    url = "https://api.worldnewsapi.com/search-news"
    params = {
        "api-key": api_key,
        "text": "agriculture OR farming OR farmer OR crops",
        "language": "en",
        "number": 20,
        "sort": "publish-time",
        "country": "in"
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        print("[DEBUG] WorldNewsAPI response:", data)
        if "news" not in data:
            print("'news' key missing in WorldNewsAPI response")
            return []
        return data["news"]
    except Exception as e:
        print("Exception in getAgroNews:", e)
        return []

def getFertilizerRecommendation(model, nitrogen, phosphorus, potassium, temp, humidity, moisture, soil_type, crop):
    le_soil = LabelEncoder()
    fertilizerdata['Soil Type'] = le_soil.fit_transform(fertilizerdata['Soil Type'])
    le_crop = LabelEncoder()
    fertilizerdata['Crop Type'] = le_crop.fit_transform(fertilizerdata['Crop Type'])
    soil_enc = le_soil.transform([str(soil_type)])[0]
    crop_enc = le_crop.transform([crop])[0]
    user_input = [[temp,humidity,moisture,soil_enc,crop_enc,nitrogen,potassium,phosphorus]]
    prediction = model.predict(user_input)
    return prediction[0]

def getMarketPricesAllStates():
    states = ["West Bengal", "Kerala", "Uttrakhand", "Uttar Pradesh", "Rajasthan", "Nagaland", "Gujarat", "Maharashtra", "Tripura", "Punjab", "Bihar", "Telangana", "Meghalaya"]
    final_list = []
    for state in states:
        state = state.replace(" ", "+")
        govdata_url = f"https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key={govdata_api_key}&format=json&filters%5Bstate%5D={state}"
        response = requests.get(govdata_url)
        data = response.json()
        print("Market API response for", state, ":", data)  # <-- ADD THIS LINE
        for entries in data["records"]:
            final_list.append(entries)
    return final_list

def GetResponse(query):
    client = genai.Client(api_key="AIzaSyBDtPl48kRQ9gcEFP2WjBkK5Nv8q24MJLs")
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=query
    )
    return response.text
