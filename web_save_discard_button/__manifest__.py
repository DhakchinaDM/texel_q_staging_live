# Copyright (C) 2023-TODAY Synconics Technologies Pvt. Ltd. (<http://www.synconics.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Save & Discard Buttons",
    "version": "17.5",
    "summary": "Save & Discard Buttons",
    "license": "AGPL-3",
    "category": "Tools",
    "author": "Synconics Technologies Pvt. Ltd., Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web",
    "maintainers": ["synconics"],
    "depends": ["web"],
    "data": [],
    "images": ["static/description/main_screen.png"],
    "assets": {
        "web.assets_backend": [
            "web_save_discard_button/static/src/scss/indicator_button.scss",
            "web_save_discard_button/static/src/xml/template.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
