from aiogram.fsm.state import State, StatesGroup

class ProfileForm(StatesGroup):
  name = State()
  faculty = State()
  degree = State()
  subject= State()
  goal = State()

class SearchState(StatesGroup):
  browsing = State()
