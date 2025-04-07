default_schedule = {
    "duration": 80,
    "breaks": [10, 20, 10, 10],
    "start_time": "08:30",
    "auto_save": 60,
    "repeat": 1,
    "theme": ["dark", "red"],
    "subjects": [
        {
            "id": 1,
            "name": "Mathematics",
            "teacher": 2,
            "zoom_link": "https://zoom.com/lesson1",
            "color": "red",
        },
        {
            "id": 2,
            "name": "Ukrainian Language",
            "teacher": 1,
            "zoom_link": "https://zoom.com/lesson2",
            "color": "red",
        },
        {
            "id": 3,
            "name": "Biology",
            "teacher": 4,
            "zoom_link": "https://zoom.com/lesson3",
            "color": "red",
        },
        {
            "id": 4,
            "name": "Physics",
            "teacher": 5,
            "zoom_link": "https://zoom.com/lesson4",
            "color": "red",
        },
        {
            "id": 5,
            "name": "Informatics",
            "teacher": 3,
            "zoom_link": "https://zoom.com/lesson5",
            "color": "red",
        },
    ],
    "teachers": [
        {
            "id": 1,
            "name": "John Doe",
            "phone": "@RTOMK",
        },
        {
            "id": 2,
            "name": "Jane Smith",
            "phone": "@Ponosnegra00",
        },
        {
            "id": 3,
            "name": "Mark Brown",
            "phone": "@weast_QQ",
        },
        {
            "id": 4,
            "name": "Emily White",
            "phone": "09340004",
        },
        {
            "id": 5,
            "name": "Alice Green",
            "phone": "09340005",
        },
    ],
    "schedule": [{"week1": [1,2,3,4,5], "week2": [3], "week3": [2], "week4": [1]} for _ in range(7)],
}
