from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    allergies = State()
    preferences = State()
    fridge = State()


class FridgeStates(StatesGroup):
    waiting_for_products = State()


class PreferenceStates(StatesGroup):
    waiting_for_allergy = State()
    waiting_for_preference = State()
