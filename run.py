import code

code.run(
    url='',  # Trailmix, Trail or Module URL
    csv_output_dir='.',  # . to generate output in this directory
    audio_output_dir=r'.',  # E.g. your anki media directory
    split_after_x_chars=500,  # Attempts to split after X (before new 'sections'), just increase the number to a huge amount to ensure each unit is one card each
    redo_completed=False,  # Should it skip tiles that have a green tick already? (On trails)

    generate_tts=True,
    tts_service='OpenAI',  # OpenAI or Azure
    open_ai_key='',
    azure_key='',
    azure_region='',

    log_into_google=True,  # If you select No, the code will wait for you to log in and confirm when you're done
    google_username='',
    google_password=''
)
