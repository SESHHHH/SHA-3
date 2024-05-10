import codecs


w = 64  # длина слова в битах для состояния S
count_rounds = 24  # число раундов


def shift_left(x, n):
    """
        Функция циклического сдвига числа x влево на n бит
        Сдвигаем число x на n бит влево (x << n)
        Вытолкнутые слева биты перемещаем вправо, т.е. перемещаем их из старших в младшие (x >> (w - n))
        OR | - побитовое ИЛИ этих операций даёт циклический сдвиг
        Применяем маску ((1 << w) - 1), для того, чтобы число оставалось в пределах w бит
    """
    n = n % w  # Приведение количества сдвигаемых бит к допустимому диапазону w

    return ((x << n) | (x >> (w - n))) & ((1 << w) - 1)


def theta(array):
    """
        Шаг theta функции перестановки
        C и D - w-битные временные значения
        Индексирование выполняем по mod 5
        Для каждой колонки возвращаем XOR с четностями двух соседних колонок
    """
    # Линия, хранящая четность каждого столбца (XOR элементов столбца)
    C = [array[i][0] ^ array[i][1] ^ array[i][2] ^ array[i][3] ^ array[i][4] for i in range(5)]
    # Заполнитель, хранящий XOR элемента C из предыдущего столбца и элементом C из следующего столбца, сдвинутого на
    # 1 бит влево
    D = [C[(i - 1) % 5] ^ shift_left(C[(i + 1) % 5], 1) for i in range(5)]

    # Для каждой линии применяем XOR с D - обновляем каждый бит состояния на основе других бит его столбца
    output_array = [[array[i][j] ^ D[i] for j in range(5)] for i in range(5)]

    return output_array


def rho_phi(array):
    """
        Шаг rho и phi функции перестановки
        rho - циклический сдвиг линии на (t + 1) * (t + 2) // 2
        phi - поворачивание каждого среза в соответствии с модульным линейным преобразованием
    """
    output_array = array.copy()

    (i, j) = (1, 0)
    # Текущий срез перестановки и вращения
    current = output_array[i][j]

    for t in range(count_rounds):
        (i, j) = (j, (2 * i + 3 * j) % 5)
        (current, output_array[i][j]) = (output_array[i][j], shift_left(current, (t + 1) * (t + 2) // 2))

    return output_array


def chi(array):
    """
        Шаг chi функции перестановки
        Побитовое преобразование каждой строки в соответствии с нелинейной функцией
    """
    output_array = array.copy()

    for j in range(5):
        column = [array[i][j] for i in range(5)]
        for i in range(5):
            output_array[i][j] = column[i] ^ ((~column[(i + 1) % 5]) & (column[(i + 2) % 5]))

    return output_array


def iota(array, RC):
    """
        Шаг iota функции перестановки
        Вносит линейный элемент, изменяя фиксированный элемент матрицы состояния array[0][0]
        RC - константа круга
        Сдвигаем RC влево на один бит и если старший бит RC = 1, то XOR c 0x71, ограничиваем результат 8 битами
    """
    output_array = array.copy()
    for i in range(7):
        RC = ((RC << 1) ^ ((RC >> 7) * 0x71)) % 256
        # Если второй бит RC = 1
        if (RC & 2):
            # Вычисляем 2 в степени i (1 << i), получаем позиции битов и устанавливаем туда 1
            output_array[0][0] = output_array[0][0] ^ (1 << ((1 << i) - 1))

    return RC, output_array


def permutation_func(array, RC=1):
    """
        Функция перестановки (из последовательных шагов) для 24 раундов
    """
    output_array = array.copy()
    for round_idx in range(count_rounds):
        RC, output_array = iota(chi(rho_phi(theta(output_array))), RC)

    return output_array


def bits_to_byte(bits):
    """
        Функция преобразования битовой последовательности состояния в один байт
    """
    byte = 0
    for i in range(8):
        byte |= bits[i] << 8 * i
    return byte


def byte_to_bits(byte):
    """
        Функция преобразования одного байта в битовую последовательность
    """
    bits = []
    for i in range(8):
        bits.append((byte >> 8 * i) % 256)
    return bits


def create_state(state):
    """
        Функция создания нового состояния из предыдущего с помощью функции перестановки
    """
    # Преобразование состояния в массив 5x5 слов длиной w=64 бита
    state_array = [[bits_to_byte(state[8 * (i + 5 * j): 8 * (i + 5 * j) + 8]) for j in range(5)] for i in range(5)]
    # Применяем функцию перестановок к массиву state
    state_array = permutation_func(state_array)
    # Инициализируем размер состояния S в байтах
    new_state = bytearray(1600//8)

    # Добавляем перестановки в новое состояние
    for i in range(5):
        for j in range(5):
            new_state[8 * (i + 5 * j):8 * (i + 5 * j) + 8] = byte_to_bits(state_array[i][j])

    return new_state


def sha3(bytes_input, output_hash_size=256, padding=0x06, rate=1088, capacity=512, bit_state_size=1600):
    """
        Функция реализации губчатого алгоритма SHA-3, состоящего из впитывания и выжимания
        bytes_input - байтовая последовательность входных данных
        output_hash_size - длина хэш-фукнции на выходе в битах
        padding - префикс, необходимый для инициализации конца обрабатываемых данных
        rate - битовая скорость
        capacity - мощность
        bit_state_size - битовый размер состояния
    """
    # Конвертация размера массива состояния в байты
    byte_state_size = bit_state_size // 8
    # Конвертация битовой скорости в байты
    byte_rate = rate // 8
    # Инициализация выходного значения хэша
    output_hash = bytearray()
    output_hash_byte_size = output_hash_size // 8
    # Инициализация состояния S, заполненного нулями
    state = bytearray([0 for _ in range(byte_state_size)])
    # Размер обрабатываемого блока данных
    block_size = 0
    # Отслежка обработанных данных в совокупности
    input_offset = 0

    # Впитывание - XOR входных данных с текущим состоянием
    while input_offset < len(bytes_input):
        # Если оставшаяся часть входных данных меньше, чем битовая скорость r
        block_size = min(len(bytes_input) - input_offset, byte_rate)
        # XOR текущего состояния с блоком данных
        for i in range(block_size):
            state[i] = state[i] ^ bytes_input[i + input_offset]
        # Увеличиваем уже обработанные данные
        input_offset = input_offset + block_size
        # Создаем состояние с функцией перестановок, если блок данных полностью обработан
        if block_size == byte_rate:
            state = create_state(state)
            block_size = 0

    # Добавление байта padding в конец данных
    state[block_size] = state[block_size] ^ padding
    # Завершение впитывания
    # Проверка заполнен ли текущий блок данных до одного байта до его полной ёмкости
    # Выполняем преобразование состояния перед добавлением padding
    if block_size == (byte_rate - 1):
        state = create_state(state)
    # Добавление паддинга в конец сообщения для обозначения его завершения
    state[byte_rate - 1] = state[byte_rate - 1] ^ 0x80
    # Обновление состояния
    state = create_state(state)

    # Выжимание
    while output_hash_byte_size > 0:
        block_size = min(output_hash_byte_size, byte_rate)
        output_hash = output_hash + state[0:block_size]
        output_hash_byte_size = output_hash_byte_size - block_size
        if output_hash_byte_size > 0:
            state = create_state(state)

    return output_hash


input_file = open('input.txt', 'rb')
input_text = codecs.decode(input_file.read())
print(input_text.encode())

digest = sha3(input_text.encode())
print(digest)

utf8_digest = codecs.decode(codecs.encode(digest, 'hex'), 'utf-8')
print(utf8_digest)

output_file = 'output.txt'
with open(output_file, 'w') as f:
    f.write(utf8_digest)
