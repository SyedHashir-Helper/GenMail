import streamlit as st
from streamlit_quill import st_quill
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import numpy as np
import pandas as pd
from io import BytesIO, StringIO
from groq import Groq
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import base64

# https://drive.google.com/file/d/1G2c_kKv5McZs-PHl1qPFK8XWak_aEHyr/view?usp=drive_link
logo_url = "https://s3.ap-southeast-2.amazonaws.com/incog-files.dev/Arrow.png"
# Initialize session state
if 'show_signature' not in st.session_state:
    st.session_state['show_signature'] = False

if 'signature_confirmed' not in st.session_state:
    st.session_state['signature_confirmed'] = False

if 'generated_content' not in st.session_state:
    st.session_state['generated_content'] = ""

if 'subject_line' not in st.session_state:
    st.session_state['subject_line'] = ""

# Sidebar for Credentials
with st.sidebar:
    st.header("Credentials")
    google_account = st.text_input("Google Account Email")
    google_app_password = st.text_input("Google App Password", type="password")
    api_key = st.text_input("API Key", type="password")

# Function to generate content using Groq API
def generate(api_key, user_input):
    client = Groq(api_key=api_key)
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": f"""
                You are an expert email composer known for crafting concise, compelling messages with impeccable grammar and a professional tone. Your writing is always on-point and engaging.
                Your task is to generate an email to concerned person based on the following input: {user_input}
                Please provide only:

                A relevant, attention-grabbing subject line
                Greetings like Dear Concerned Person,
                and then only The main body of the email

                Ensure your content is:

                Direct and specific
                Positively framed
                Grammatically flawless
                Professional in tone
                Tailored to the receiver

                Exclude any closings, or unnecessary text. Begin with the subject line (always on first line) and end with the main body.
                """,
            }
        ],
        model="llama3-8b-8192",
    )
    return chat_completion.choices[0].message.content

# Function to send email with attachment
def send_email_with_attachment(sender_email, sender_password, recipient_email, subject, message, attachments):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    # Attach the message body
    body = MIMEText(message, 'html')
    msg.attach(body)

    # Attach each file
    for file in attachments:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(file['content'])
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{file["filename"]}"')
        msg.attach(part)

    context = ssl.create_default_context()

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())

col1, col2 = st.columns([1, 4])  # Adjust the ratio as needed

# Title of the app with logo
st.markdown(f"""
    <h1 style="display: flex; align-items: center;">
        <img src="{logo_url}" alt="App Logo" style="width: 150px; height: auto; margin-right: 15px;">
        GenMail
    </h1>
    """, unsafe_allow_html=True)

# Input fields
col1, col2 = st.columns(2)

with col1:
    st.subheader("Recipient Email")
    receiver_emails_text = st.text_area("Enter receiver emails (comma-separated)", "")
    receiver_email_file = st.file_uploader("Or upload a CSV file with receiver emails", type=["csv"])

with col2:
    st.subheader("CC Emails")
    cc_emails_text = st.text_area("Enter CC emails (comma-separated)", "")
    cc_file = st.file_uploader("Or upload a CSV file with CC emails", type=["csv"])


prompt = st.text_area("Enter the main content or prompt for the email")

# Process CSV files
def process_csv(uploaded_file):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        if 'email' in df.columns:
            return df['email'].tolist()
        else:
            st.error("CSV file must contain an 'email' column.")
    return []

receiver_emails = process_csv(receiver_email_file)
cc_emails = process_csv(cc_file)

# Combine direct input with CSV uploads
if receiver_emails_text:
    receiver_emails.extend(email.strip() for email in receiver_emails_text.split(','))

if cc_emails_text:
    cc_emails.extend(email.strip() for email in cc_emails_text.split(','))

# Display the email addresses
st.write("### Recipients")
st.write("Receivers:", receiver_emails)
st.write("CC Emails:", cc_emails)

# Button to generate email and content
if st.button("Generate Email"):
    if prompt and api_key:
        st.session_state['show_signature'] = True
        if receiver_emails:
            generated_content = generate(api_key, prompt)
            lines = generated_content.split('\n', 1)
            if len(lines) >= 2:
                st.session_state['subject_line'] = lines[0].strip()
                st.session_state['generated_content'] = lines[1].strip()
            else:
                st.session_state['subject_line'] = ""
                st.session_state['generated_content'] = generated_content
        else:
            st.warning("No receiver emails found. Please provide emails directly or upload a valid CSV file.")
    else:
        st.warning("Please fill in all the fields to generate the email and content.")

# Display the subject line and generated content directly in st_quill
if st.session_state['generated_content']:
    st.write("### Subject Line")
    st.text_input("Subject Line", st.session_state['subject_line'], key='subject_line')

    st.write("### Email Content")
    final_email = f"<div class='preview-box'>{st.session_state['generated_content']} <br><br></div>"
    st.session_state['generated_content'] = st_quill(final_email, key='email_content', html=True)

    # Signature input boxes
    if st.session_state['show_signature']:
        st.write("### Signature Section")

        # Closing Signature (Text)
        closing_signature = st_quill("Closing Signature (e.g., 'Best Regards, [Your Name]')", key='closing_signature', html=True, )
        col1, col2 = st.columns([3, 2])  # Adjust column width ratios as needed

        with col1:
            # Signature drawing canvas
            st.write("Draw your signature below:")
            canvas_result = st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)",  # Fill color with opacity
                stroke_width=2,
                stroke_color="#000000",
                background_color="#ffffff",
                update_streamlit=True,
                height=150,
                width=400,
                drawing_mode="freedraw",
                key="canvas"
            )

        with col2:
            # Signature image upload
            st.write("OR Upload a signature image below:")
            uploaded_image = st.file_uploader("Choose an image...", type=["png", "jpg", "jpeg"])

            if uploaded_image is not None:
                # Save uploaded image to BytesIO
                uploaded_image_bytes = BytesIO()
                try:
                    image = Image.open(uploaded_image)
                    image.save(uploaded_image_bytes, format="PNG")
                    uploaded_image_bytes.seek(0)  # Rewind the file pointer to the beginning
                    st.image(image, caption="Uploaded Signature Image", use_column_width=True)
                except Exception as e:
                    st.error(f"Error processing the uploaded image: {e}")

        if st.button("Confirm Signature"):
            st.session_state['signature_confirmed'] = True
            st.success("Signature confirmed and saved!")

        if st.session_state['signature_confirmed']:
            # Create the full email body with signature
            signature_img_tags = []
            
            if canvas_result.image_data is not None:
                image = Image.fromarray(canvas_result.image_data)
                buffered = BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                # signature_img_tags.append(f'<img src="data:image/png;base64,{img_str}" alt="Signature" style="max-width: 300px; height: auto;" />')

            if uploaded_image is not None:
                img_str = base64.b64encode(uploaded_image_bytes.getvalue()).decode()
                # signature_img_tags.append(f'<img src="data:image/png;base64,{img_str}" alt="Signature" style="max-width: 300px; height: auto;" />')

            # Attachments list
            attachments = []
            if canvas_result.image_data is not None:
                buffered = BytesIO()
                image.save(buffered, format="PNG")
                attachments.append({
                    'filename': 'signature_.png',
                    'content': buffered.getvalue()
                })
            if uploaded_image is not None:
                attachments.append({
                    'filename': 'signature_.png',
                    'content': uploaded_image_bytes.getvalue()
                })

            # Send Email button
            if st.button("Send Email", key="send_email"):
                body_with_signature = f"<div>{st.session_state['generated_content']} <br> <br> {closing_signature}</div>"
                smtp_server = "smtp.gmail.com"
                port = 587
                user_email = google_account
                password = google_app_password
                if password:
                    send_email_with_attachment(
                        sender_email=user_email,
                        sender_password=password,
                        recipient_email=','.join(receiver_emails),
                        subject=st.session_state['subject_line'],
                        message=body_with_signature,
                        attachments=attachments
                    )
                    st.markdown(body_with_signature, unsafe_allow_html=True)
                else:
                    st.warning("Please enter your Google App Password to send the email.")
        elif closing_signature or (canvas_result.image_data is not None or uploaded_image is not None):
            st.warning("Please complete both signature fields and confirm your signature.")
