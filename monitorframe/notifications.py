import abc
import smtplib

from email.mime.text import MIMEText
from typing import Union


class EmailInterface(abc.ABC):

    @abc.abstractmethod
    def build_message(self):
        pass

    @abc.abstractmethod
    def send(self):
        pass


class Email(EmailInterface):
    """Class representation for constructing and sending an email notification."""
    def __init__(self, username: str, subject: str, content: str, recipients: Union[str, list]):
        self.sender = f'{username}@stsci.edu'
        self.subject = subject
        self.content = content
        self.recipients = self._set_recipients(recipients)

        self.message = self.build_message()

    @staticmethod
    def _set_recipients(recipients_input):
        """Set recipient or format list of recipients."""
        if isinstance(recipients_input, list):
            return ', '.join(recipients_input)

        if isinstance(recipients_input, str):
            return recipients_input

        raise TypeError(
            f'recipients must either be a list or a string. Recieved {type(recipients_input)} instead.'
        )

    def build_message(self) -> MIMEText:
        """Create MIMEText object."""

        message = MIMEText(self.content)
        message['Subject'] = self.subject
        message['From'] = self.sender
        message['To'] = self.recipients

        return message

    def send(self):
        """Send constructed email."""

        with smtplib.SMTP('smtp.stsci.edu') as mailer:
            mailer.send_message(self.message)
