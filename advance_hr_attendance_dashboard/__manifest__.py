{
    "name": "Advance HR Attendance Dashboard",
    "version": "17.12",
    "category": "Human Resources",
    "summary": """This module helps you to view leaves of employee based on
     different leave types.""",
    "description": """Advance HR Attendance Dashboard helps for 
     filtering attendance data,  finding specific employees attendance data,
     and for displaying attendance information, also we can print the
     attendance in pdf format .""",
    "author": "Cybrosys Techno Solutions",
    "company": "Cybrosys Techno Solutions",
    "maintainer": "Cybrosys Techno Solutions",
    "website": "https://www.cybrosys.com",
    "depends": ["hr_holidays", "hr", "hr_attendance"],
    "data": [
        "views/hr_leave_type_views.xml",
        "views/advance_hr_attendance_dashboard_menus.xml",
        "views/res_config_settings_views.xml",
        "report/hr_attendance_reports.xml",
        "report/hr_attendance_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "advance_hr_attendance_dashboard/static/src/xml/attendance_dashboard_templates.xml",
            "advance_hr_attendance_dashboard/static/src/js/attendance_dashboard.js",
            "advance_hr_attendance_dashboard/static/src/scss/attendance_dashboard.scss",
        ],
    },
    "external_dependencies": {
        "python": ["pandas"],
    },
    "images": [
        "static/description/banner.jpg",
    ],
    "license": "AGPL-3",
    "installable": True,
    "auto_install": False,
    "application": False,
}
