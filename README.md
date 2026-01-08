# fancontrol
When moving onto Linux on the desktop I had been using the standard "fancontrol" scripts as a means of controlling system fans, but switching to a passively cooled Nvidia I needed something that would work with information gathered from the native tools for it. Ideally I should have just modified, but dealing with a lengthy bash-script simply wasn't in the category of fun things to spend my time doing. So I made a replacement for it in Python instead, probably reinventing every wheel imaginable because that's something I felt like doing.

![fancontrol](pictures/Screenshot%20from%202026-01-08%2023:14:40.png)

The tool should be able to import already existing bash-configuration if so desired via `pwmimport.py`, but otherwise you can use the interactive command-line tool `fanconfig.py` in order to create the needed configuration. You will need to figure out which "pwm"-entry corresponds to a specific fan, ideally only one of them at a time. One point of importance is that considering that we are living in the age of aquarius, the UEFI is probably the better bet for controlling fans unless you need specific behavior such as ensuring a quiet working environment, controlled heating when playing games etc. This means that you will be better off leaving critical fans under the control of the chipset, then allowing the script to control the auxilliary case fans.

![fanconfig](pictures/Screenshot%20from%202026-01-08%2023:17:20.png)
