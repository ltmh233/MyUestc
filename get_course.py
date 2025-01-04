import requests

def get_course_schedule(username):
    url = f'https://studyapi.uestc.edu.cn/ckd/getWeekClassSchedule?userId={username}'
    response = requests.get(url)
    return response.json()

def get_current_week():
    url = 'https://studyapi.uestc.edu.cn/ckd/getWeek'
    response = requests.get(url)
    return response.json()