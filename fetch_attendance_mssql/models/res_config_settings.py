from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    _description = 'Res Config Settings'

    ip_address = fields.Char(string='Server IP', help="Specify the IP address.",
                             config_parameter="fetch_attendance_mssql.ip_address")
    mssql_db_name = fields.Char(string='Database Name', help="Specify the name of the MSSQL database.",
                                config_parameter="fetch_attendance_mssql.mssql_db_name")

    mssql_db_user = fields.Char(string='Database User', help="Specify the user for connecting to the MSSQL database.",
                                config_parameter="fetch_attendance_mssql.mssql_db_user")
    mssql_db_password = fields.Char(string='Database Password',
                                    help="Specify the password for the MSSQL database user.",
                                    config_parameter="fetch_attendance_mssql.mssql_db_password")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update({
            'ip_address': self.env['ir.config_parameter'].sudo().get_param(
                'fetch_attendance_mssql.ip_address', default=False),
            'mssql_db_name': self.env['ir.config_parameter'].sudo().get_param(
                'fetch_attendance_mssql.mssql_db_name', default=False),
            'mssql_db_user': self.env['ir.config_parameter'].sudo().get_param(
                'fetch_attendance_mssql.mssql_db_user', default=False),
            'mssql_db_password': self.env['ir.config_parameter'].sudo().get_param(
                'fetch_attendance_mssql.mssql_db_password', default=False),
        })
        return res

    def set_values(self):
        self.env['ir.config_parameter'].sudo().set_param('fetch_attendance_mssql.ip_address', self.ip_address)
        self.env['ir.config_parameter'].sudo().set_param('fetch_attendance_mssql.mssql_db_name', self.mssql_db_name)
        self.env['ir.config_parameter'].sudo().set_param('fetch_attendance_mssql.mssql_db_user', self.mssql_db_user)
        self.env['ir.config_parameter'].sudo().set_param('fetch_attendance_mssql.mssql_db_password',
                                                         self.mssql_db_password)
        super(ResConfigSettings, self).set_values()
