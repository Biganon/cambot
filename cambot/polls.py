import nextcord

class Poll:
    def __init__(self):
        self.message = None
        self.owner = None
        self.intro = None
        self.options = {}

class Button(nextcord.ui.Button):
    def __init__(self, owner):
        super().__init__(label=f"Supprimer le sondage ({owner.display_name} uniquement)",
                         emoji="\N{cross mark}")
        self.owner = owner

    async def callback(self, interaction):
        if interaction.user == self.owner:
            await interaction.message.delete()

class ButtonView(nextcord.ui.View):
    def __init__(self, owner):
        super().__init__(timeout=None)
        self.add_item(Button(owner=owner))