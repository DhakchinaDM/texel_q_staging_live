{
    'name': 'Send Payslip Via Mail',
    'version': '17.1',
    'summary': '',
    'description': """ HR Payroll Extended """,
    'category': 'Human Resources/Employees',
    'author': 'AppsComp Widgets Pvt Ltd',
    'website': 'https://www.appscomp.com',
    'depends': ['hr', 'hr_payroll', 'base',],
    'data': [
        'data/mail_template.xml',
        'views/hr_payslip_view.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
