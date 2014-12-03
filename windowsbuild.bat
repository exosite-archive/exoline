pip install --upgrade -r requirements.txt
pyinstaller exo.spec --noconfirm
copy dist\exo\exo.exe dist\exo\exo
python innosetup.py
iscc innosetup.iss
for /f "delims=" %%A in ('python -c "import exoline ; print(exoline.__version__)"') do @set exoline_version=%%A
if exist "E:\exoline_builds" (
    copy Output\setup.exe E:\exoline_builds\exoline-%exoline_version%-setup.exe
    @echo Installer is here: 
    @echo E:\exoline_builds\exoline-%exoline_version%-setup.exe
) else (
    copy Output\setup.exe Output\exoline-%exoline_version%-setup.exe
    @echo Installer is here: 
    @echo Output\exoline-%exoline_version%-setup.exe
)
@echo Now would be a good time to push any changes to innosetup.iss:
git diff
