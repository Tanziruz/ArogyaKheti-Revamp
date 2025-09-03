import datetime
from django.shortcuts import render, redirect
from .models import User, Produce
from .forms import CropRecommendationForm, FertilizerPredictionForm, UserInputForm, CropProduceListForm, DiseaseDetectionForm
import pickle, numpy as np
from django.template.defaulttags import register
from .functions import getWeatherDetails, getAgroNews, getFertilizerRecommendation, getMarketPricesAllStates, GetResponse
import google.generativeai as genai
import os
from PIL import Image
import io

# Configure Gemini AI
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

cropRecommendationModel = pickle.load(open('model_code/CropRecommend.pkl', 'rb'))
fertilizerRecommendModel = pickle.load(open('model_code/Fertilizer.pkl', 'rb'))

@register.filter
def get_range(value):
    return range(value)

@register.filter
def index(indexable, i):
    return indexable[i]

def getDetailsFromUID(id):
    obj = User.objects.get(id=id)
    return obj

def analyze_plant_disease(image_file):
    """
    Analyze plant disease using Gemini AI
    """
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Convert uploaded file to PIL Image
        image = Image.open(image_file)
        
        # Create simple prompt
        prompt = """
        Analyze this plant leaf image and provide ONLY:
        1. Disease name (or "Healthy Plant" if no disease)
        2. How it occurs (exactly 15 words)
        3. How to prevent (exactly 30 words)
        
        Format as JSON:
        {
            "name": "disease name",
            "reasons": "how it occurs in 15 words",
            "fix": "prevention in 30 words"
        }
        """
        
        # Generate response
        response = model.generate_content([prompt, image])
        
        # Parse the response
        import json
        try:
            response_text = response.text
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            json_str = response_text[start_idx:end_idx]
            result = json.loads(json_str)
        except:
            # Fallback response
            result = {
                "name": "Disease Detection Complete",
                "reasons": response.text[:60] if response.text else "Analysis completed",
                "fix": "Consult agricultural expert for proper treatment and follow good farming practices"
            }
        
        return result
        
    except Exception as e:
        return {
            "name": "Analysis Error",
            "reasons": f"Error: {str(e)[:50]}",
            "fix": "Please try uploading a clearer image or check your internet connection"
        }

def e404_page(request):
    try:
        error_message = request.session["error_message"]
        return render(request, "dash/404.html", context={
            "errormsg" : error_message
        })
    except:
        return render(request, "dash/404.html")


def home_page(request):
    # try: 
    id = request.session["member_logged_id"]
    userlogged = getDetailsFromUID(id)

    try:
        my_products = Produce.objects.filter(farmerid = userlogged.id)
        last = my_products.last()
    except:
        my_products = []
        last = ""
    
    try:
        public_products = Produce.objects.all()
        last = my_products.last()
    except:
        public_products = []
        last = ""

    details = getWeatherDetails(userlogged.coords)
    news = getAgroNews()
    context = {
        "user": userlogged,
        "produces": my_products,
        "produces_count": len(my_products),
        "public_produces_count": len(public_products),
        "last_listing": last,
        'news': news[:3],
        'weather': details,
    }
    return render(request, 'dash/home.html', context)
    
def forum(request):
    try:
        return render(request, 'dash/forum.html')
    except:
        request.session["error_message"] = "Please Login to Continue"
        return redirect((f'/admin/404/'))

def croprec(request):
    try:
        logged_id = request.session["member_logged_id"]
        userlogged = getDetailsFromUID(logged_id)
        
        if request.method == 'POST':
            form = CropRecommendationForm(request.POST)
            weatherd = getWeatherDetails(userlogged.coords)
            if form.is_valid():
                nitrogen = form.cleaned_data['nitrogen']
                phosphorus = form.cleaned_data['phosphorus']
                potassium = form.cleaned_data['potassium']
                rainfall = form.cleaned_data['rainfall']
                PH = form.cleaned_data['PH']
                temp = weatherd[1]
                humidity = weatherd[2]
                data = np.array([[nitrogen, phosphorus, potassium, temp, humidity, PH, rainfall]])
                prediction = cropRecommendationModel.predict(data)
                context = {
                    'form': form,
                    'user': userlogged,
                    'userid': userlogged.id,
                    'prediction': prediction[0]
                }
        else:
            form = CropRecommendationForm()
            context = {
                "form": form,
                'userid': userlogged.id,
                'user': userlogged,    
            }

        return render(request, 'dash/tools/crop_rec.html', context)
    except:
        request.session["error_message"] = "Please Login to Continue"
        return redirect((f'/admin/404/'))

def news_page(request):
    try:
        logged_id = request.session["member_logged_id"]
        userlogged = getDetailsFromUID(logged_id)

        news = getAgroNews()
        context = {
            'news': news,
            'user': userlogged,
            'userid': userlogged.id,
        }
        return render(request, 'dash/news.html', context)
    except:
        request.session["error_message"] = "Please Login to Continue"
        return redirect((f'/admin/404/'))

def fertrec(request):
    try:
        logged_id = request.session["member_logged_id"]
        userlogged = getDetailsFromUID(logged_id)
        
        if request.method == 'POST':
            form = FertilizerPredictionForm(request.POST)
            weatherd = getWeatherDetails(userlogged.coords)
            if form.is_valid():
                nitrogen = form.cleaned_data['nitrogen']
                phosphorus = form.cleaned_data['phosphorus']
                potassium = form.cleaned_data['potassium']
                moisture = form.cleaned_data['moisture']
                soil_type = form.cleaned_data['soil_type']
                crop = form.cleaned_data['crop']
                temp = weatherd[1]
                humidity = weatherd[2]
                prediction = getFertilizerRecommendation(fertilizerRecommendModel, nitrogen, phosphorus, potassium, temp, humidity, moisture, soil_type, crop)
                context = {
                    'form': form,
                    'user': userlogged,
                    'userid': userlogged.id,
                    'prediction': prediction
                }
        else:
            form = FertilizerPredictionForm()
            context = {
                "form": form,
                "user": userlogged,
                'userid': userlogged.id,
            }

        return render(request, 'dash/tools/fert_rec.html', context)
    except:
        request.session["error_message"] = "Please Login to Continue"
        return redirect((f'/admin/404/'))

def crop_prices_page(request):
    try:
        logged_id = request.session["member_logged_id"]
        userlogged = getDetailsFromUID(logged_id)

        try:
            latest_prices = request.session["latest_prices"]
        except:
            latest_prices = getMarketPricesAllStates()
            request.session["latest_prices"] = latest_prices
    
        context = {
            "userid": userlogged.id,
            "user": userlogged,
            "date": datetime.datetime.now(),
            "prices": latest_prices
        }

        return render(request, 'dash/check_prices.html', context)
    except Exception as e:
        print("Error in crop_prices_page:", e)
        request.session["error_message"] = str(e)
        return redirect((f'/admin/404/'))

def help_page(request):
    try:
        logged_id = request.session["member_logged_id"]
        userlogged = getDetailsFromUID(logged_id)

        if request.method == 'POST':
            form = UserInputForm(request.POST)
            if form.is_valid():
                try:
                    existinglog = request.session["chatlog"]
                    del request.session['chatlog']
                except:
                    pass

                query = form.cleaned_data['userinput']
                res = GetResponse(query)
                try:
                    existinglog = request.session["chatlog"]
                    existinglog['queries'].append(query)
                    existinglog['responses'].append(res)
                    request.session['chatlog'] = existinglog

                except:
                    request.session["chatlog"] = {
                        'queries': [query],
                        'responses': [res]
                    }
                
                log = request.session["chatlog"]
                context = {
                    'userid': userlogged.id,
                    'user': userlogged,
                    'log' : log,
                    'form' : form,
                }

        else:
            form = UserInputForm()
            context={
                "userid": userlogged.id,
                'form': form,
                "user": userlogged,
            }

        return render(request, 'dash/help.html', context)
    except Exception as e:
        print(e)
        request.session["error_message"] = "Please Login to Continue"
        return redirect((f'/admin/404/'))

def profile_page(request):
    try:
        logged_id = request.session["member_logged_id"]
        userlogged = getDetailsFromUID(logged_id)

        context = {
            "userid": userlogged.id,
            "user": userlogged,
        }

        return render(request, 'dash/profile.html', context)
    except:
        request.session["error_message"] = "Please Login to Continue"
        return redirect((f'/admin/404/'))

def logout_view(request):
    if request.session["member_logged_id"] != None:
        del request.session["member_logged_id"]
        return redirect('/')
    else:
        request.session["error_message"] = "You are not logged in yet."
        return redirect((f'/admin/404/'))
    
def list_page(request):
    try:
        logged_id = request.session["member_logged_id"]
        userlogged = getDetailsFromUID(logged_id)
        
        if request.method == 'POST':
            form = CropProduceListForm(request.POST)
            if form.is_valid():
                try:
                    Produce.objects.create(**form.cleaned_data, farmerid = int(userlogged.id), unit="quintals")
                    context = {
                        'form': form,
                        'user': userlogged,
                        'userid': userlogged.id,
                        'success': "Your produce has been listed."
                    }
                except Exception as e:
                    context = {
                        'form': form,
                        'user': userlogged,
                        'userid': userlogged.id,
                        'success': e,
                    }
        else:
            form = CropProduceListForm()
            context = {
                "form": form,
                'userid': userlogged.id,
                'user': userlogged,    
            }
        return render(request, "dash/market/list_produce.html", context)
    except:
        request.session["error_message"] = "Please login to continue"
        return redirect((f'/admin/404/'))

def check_my_listings(request):
    try:
        logged_id = request.session["member_logged_id"]
        userlogged = getDetailsFromUID(logged_id)

        produces = Produce.objects.all()

        context = {
            'user': userlogged,
            'produces':produces
        }
        return render(request, "dash/market/check_produces.html", context)
        
    except Exception as e:
        request.session["error_message"] = "Please Login to Continue"
        return redirect((f'/admin/404/'))

def delete_listing(request, id):
    try:
        logged_id = request.session["member_logged_id"]
        userlogged = getDetailsFromUID(logged_id)

        listing = Produce.objects.get(id=id)
        listing.delete()
        return redirect('/admin/check_products')

    except Exception as e:
        request.session["error_message"] = "Please Login to Continue"
        return redirect((f'/admin/404/'))

def disease_detection(request):
    try:
        logged_id = request.session["member_logged_id"]
        userlogged = getDetailsFromUID(logged_id)
        prediction = None

        if request.method == 'POST':
            form = DiseaseDetectionForm(request.POST, request.FILES)
            if form.is_valid():
                image = form.cleaned_data['image']
                # Use Gemini AI for disease detection
                prediction = analyze_plant_disease(image)
        else:
            form = DiseaseDetectionForm()

        context = {
            "form": form,
            "user": userlogged,
            "userid": userlogged.id,
            "prediction": prediction,
        }
        return render(request, "dash/tools/disease_detection.html", context)
    except:
        request.session["error_message"] = "Please Login to Continue"
        return redirect((f'/admin/404/'))