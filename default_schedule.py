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
            "name": "математика",
            "teacher": 2,
            "zoom_link": "https://vo.uu.edu.ua/course/view.php?id=21291",
            "color": "red",
        },
        {
            "id": 2,
            "name": "укр. м",
            "teacher": 1,
            "zoom_link": "https://vo.uu.edu.ua/course/view.php?id=21286",
            "color": "red",
        },
        {
            "id": 3,
            "name": "біологія",
            "teacher": 4,
            "zoom_link": "https://vo.uu.edu.ua/course/view.php?id=23529",
            "color": "red",
        },
        {
            "id": 4,
            "name": "фізика",
            "teacher": 5,
            "zoom_link": "https://vo.uu.edu.ua/course/view.php?id=23536",
            "color": "red",
        },
        {
            "id": 5,
            "name": "укр. літ",
            "teacher": 3,
            "zoom_link": "https://vo.uu.edu.ua/course/view.php?id=23536",
            "color": "red",
        },
    ],
    "teachers": [
        {
            "id": 1,
            "name": "Викладач 1",
            "phone": "@RTOMK",
        },
        {
            "id": 2,
            "name": "Викладач 2",
            "phone": "@Ponosnegra00",
        },
        {
            "id": 3,
            "name": "Викладач 3",
            "phone": "@weast_QQ",
        },
        {
            "id": 4,
            "name": "Викладач 4",
            "phone": "09340004",
        },
        {
            "id": 5,
            "name": "Викладач 5",
            "phone": "09340005",
        },
    ],
    "schedule": [{"week1": [1,2,3,4,5], "week2": [3], "week3": [2], "week4": [1]} for _ in range(7)],
}
