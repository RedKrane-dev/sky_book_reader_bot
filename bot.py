import os
import logging
from turtledemo.penrose import start

import aiofiles

from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from unicodedata import normalize, is_normalized


class BookState(StatesGroup):
    picking_book = State()
    reading_book = State()

class BookReaderBot:

    dp = Dispatcher()

    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.all_books = self.find_all_books()
        self.page_size = 500

        self.command_start_handler = self.dp.message(CommandStart())(self.command_start_handler)
        self.choose_book_handler = self.dp.message(Command('open'))(self.choose_book_handler)
        self.book_chosen = self.dp.message(BookState.picking_book, F.text.in_(self.all_books))(self.book_chosen)
        self.book_chosen_incorrectly = self.dp.message(StateFilter(BookState.picking_book))(self.book_chosen_incorrectly)
        self.next_page_book_reading = self.dp.message(Command('next'))(self.next_page_book_reading)

    def make_row_keyboard(self, items: list[str]) -> ReplyKeyboardMarkup:
        """
        Создаёт реплай-клавиатуру с кнопками в один ряд
        """
        row = [KeyboardButton(text=item) for item in items]
        return ReplyKeyboardMarkup(keyboard=[row], resize_keyboard=True)


    def find_all_books(self):
        """
        Находит все книги в директории books в корне проекта, упаковывает в список
        """
        directory = './books'
        books_list = []
        books_list += os.listdir(directory)
        return books_list

    async def file_normalize(self, book, state: FSMContext):
        """
        Распаковщик и нормализатор текста txt, удаляет спецсимволы,
        записывает выбранную книгу в стейт пользователя
        """
        async with aiofiles.open(file='./books/' + book.text, mode='r', encoding='utf-8') as f:
            file = await f.read()
            if not is_normalized('NFC', file):
                normal_file = normalize('NFC', file)
                await state.update_data(book=normal_file)
                return normal_file
            await state.update_data(book=file)
            return file

    async def command_start_handler(self, message: Message, state: FSMContext):
        """
        Обработчик команды /statr, чистит стейт пользователя, приветствует
        """
        await state.clear()
        await message.answer(
            text=f'Привет! {html.bold(message.from_user.full_name)}!\n'
                 f'Введите команду /open для вывода списка книг',
            reply_markup=self.make_row_keyboard(['/open'])
        )

    # /open
    async def choose_book_handler(self, message: Message, state: FSMContext):
        """
        Обработчик команды /open, чистит стейт пользователя,
        предлагает выбрать книгу из списка доступных
        """
        await state.clear()
        all_books_str = ',\n'.join(self.all_books)
        await message.answer(
            text=f'Выберите книгу из списка:\n{all_books_str}',
            reply_markup=self.make_row_keyboard(self.all_books)
        )
        await state.set_state(BookState.picking_book)

    async def book_chosen(self, message: Message, state: FSMContext):
        """
        Функция кладет информацию о выбранной книге в стейт, присваивает пользователю стейт 'читает книгу'
        """
        await state.update_data(chosen_book=message.text.lower(), current_page=1)
        await message.answer(text=f'Выбрана книга {message.text}, приятного чтения')
        await state.set_state(BookState.reading_book)
        await self.book_reading(message, state)

    async def book_chosen_incorrectly(self, message: Message):
        """
        Обработчик ошибок ввода книги
        """
        all_books_str = ',\n'.join(self.all_books)
        await message.answer(
            text=f'Такой книги нет.\n\n'
                 f'Выберите одну из книг из списка ниже:\n'
                 f'{all_books_str}',
            reply_markup=self.make_row_keyboard(self.all_books)
        )

    async def book_reading(self, message: Message, state: FSMContext):
        """
        Функция чтения, срабатывает автоматически с командой /open, возвращает первую страницу
        """
        normalize_file = await self.file_normalize(message, state)
        user_data = await state.get_data()
        page = user_data['current_page']
        await message.answer(
            text=f'{normalize_file[:self.page_size]}\n\n'
                    f'Книга {message.text}\n'
                    f'Страница {page}',
            reply_markup=self.make_row_keyboard(['/open', '/next'])
        )
        await state.update_data(current_page=page + 1)

    async def next_page_book_reading(self, message: Message, state: FSMContext):
        """
        Обработчик команды /next, возвращает следующую страницу книги.
        Если книга закончилась, предлагает выбрать другую
        """
        get_user_data = await state.get_data()
        page = get_user_data['current_page']
        await state.update_data(current_page=page + 1)

        user_data = await state.get_data()
        user_book = user_data['book']
        user_book_name = user_data['chosen_book']
        new_page = user_data['current_page']
        start_pos = (new_page * self.page_size) - self.page_size
        stop_pos = new_page * self.page_size
        current_text = user_book[start_pos:stop_pos]

        if current_text:
            await message.answer(
                text=f'{user_book[start_pos:stop_pos]}\n\n'
                     f'Книга {user_book_name}\n'
                     f'Страница {new_page}',
                reply_markup=self.make_row_keyboard(['/open', '/next'])
            )
        else:
            await message.answer(
                text=f'Похоже книга закончилась!\n'
                     f'Введите /open для выбора другой книги' ,
                reply_markup=self.make_row_keyboard(['/open'])
            )

    async def main(self):
        """
        Основная функция бота. Подставляет токен и запускает поллинг
        """
        bot = Bot(token=self.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        await self.dp.start_polling(bot)


