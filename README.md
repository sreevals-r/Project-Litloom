◆ LitLoom ◆
Your Personal Digital Atelier for Poetry Analysis
LitLoom is an elegant and powerful desktop application designed for poets, students, and literature enthusiasts alike. It provides a beautiful and intuitive environment to write poetry and then seamlessly unveils the intricate layers of your work through advanced analytical tools. From rhyme schemes to sentiment tone analysis, LitLoom transforms your creative process into a journey of discovery and growth.

✨ Key Features
✒️ Elegant & Themed Interface:
Vintage-inspired UI with rounded corners, custom fonts, and a warm, inviting color palette.

✍️ Intuitive Poem Editor:
A clean, focused writing space with tools like:

Example Poems: Load classic poem snippets to inspire your writing.
Interactive Spell Checker: A custom popup suggests corrections without disrupting your flow.
🗣️ Text-to-Speech (TTS):

Listen to your poems and analysis read aloud using Windows’ native SAPI5 voices through the pywin32 library.
Control playback speed and switch between installed voices easily.
Supports additional language voices after installing via Windows settings.
🔬 Comprehensive Analysis Suite:

Overview: Line count, word count, snippet preview.
Rhyme Scheme Detection: Identifies rhyme patterns (ABAB, AABB, etc.) and groups rhyming words.
Parts of Speech (POS) Tagging: Extract nouns, verbs, adjectives, and more using NLTK.
Figure of Speech Detection: Detects similes, metaphors, and alliterations with smart heuristics.
Sentimental Tone Analysis: Scores poem tone using NLTK’s VADER for positive, negative, or neutral sentiment.
🌍 Multi-Language Translation:
Translate poems into dozens of languages using the deep-translator library, perfect for multilingual poetry lovers.

📄 Professional PDF Export:
Generate a beautifully formatted PDF report with complete analysis using ReportLab, including full Unicode font support for all languages.

🚀 Getting Started
You can run LitLoom as a user with a pre-built app or from the source code if you want to develop or customize it.

1. For Users (Pre-built Executable)
Visit the Releases page.
Download the latest LitLoom.zip.
Extract it to your preferred location.
Ensure the assets folder is alongside the executable.
Double-click LitLoom.exe to start.
2. For Developers (Run from Source)
Clone the repository:
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
Create and activate a Python virtual environment:
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
Install dependencies:
pip install pyspellchecker pyttsx3 nltk deep-translator reportlab Pillow pywin32
Run the app:
python LitLoom.py
On first run, NLTK will download required data packages automatically. Make sure you are connected to the internet.
📖 How to Use LitLoom
Welcome Screen:
Launch the app and click "Let's Go!" to enter the poem editor.

Poem Editor:

Write or paste your poem.
Use Add Example to load sample poems for inspiration.
Click Spell Correct to open the spell checker popup.
Text-to-Speech (TTS):

Click the speaker icon to open TTS controls.
Choose from installed Windows voices and adjust playback speed.
To add new language voices, go to Windows:
Settings > Time & Language > Language & Region > Add a language
Install the language pack and voice for TTS.
Analyze Your Poem:

Click Analyze to generate reports.
Switch between views: Overview, Parts of Speech, Figures of Speech, and Tone.
Translate poems with the Translation button and select your target language.
Adjust Readability:

Use + and – buttons to resize text for comfortable reading.
Export to PDF:

Use Convert to PDF to save a full analysis report in a professional PDF format.
📸 Screenshots
Screenshot 2025-06-08 143849

Screenshot 2025-06-08 144136

Screenshot 2025-06-08 172819

Screenshot 2025-06-08 172933

Screenshot 2025-06-08 172953

🤝 Contributing
Contributions are warmly welcomed! To help improve LitLoom:

Fork the repo.
Create a feature branch:
git checkout -b feature/YourFeatureName
Commit your changes:
git commit -m "Add description of your feature"
Push to your branch:
git push origin feature/YourFeatureName
Open a Pull Request and describe your improvements.
📜 License
This project is licensed under the MIT License — see the LICENSE file for details.

🙏 Acknowledgments
Thanks to the amazing developers and communities behind these open-source tools used in LitLoom:

Tkinter — GUI framework
Pillow — Image processing
pyspellchecker — Spell checking
pywin32 — Windows API access for TTS
NLTK (Natural Language Toolkit) — Natural language processing
Deep-Translator — Translation services
ReportLab — PDF generation
❓ FAQ
Q: Does LitLoom work on macOS or Linux?
A: Currently, LitLoom is optimized for Windows because it uses Windows-native TTS voices via pywin32. Linux/macOS support is planned for future releases.

Q: How do I add more voices for Text-to-Speech?
A: Install additional language packs and voices via Windows Settings → Time & Language → Language & Region → Add a language. After installation, restart LitLoom to see new voices.

Q: Can I use my own fonts for PDF export?
A: The PDF export uses NotoSans by default to support multiple languages. You can customize fonts by modifying the export code in the source.

If you want, I can also help you create a short intro video GIF or generate screenshots for your README! Just ask.