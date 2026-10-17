Юсюмьели Сергей

##  Как играть и управлять квестом

### 1. Начать или продолжить игру
```bash
python quest.py play
```


### 2. Начать новую игру с самого начала
```bash
python quest.py play --new
```

### 3. Просмотр статистики концовок
* **Оба вида сразу (абсолютные числа и проценты)**:
  ```bash
  python quest.py stats
  ```
 
* **Только абсолютные числа**:
  ```bash
  python quest.py stats --view abs
  ```

* **Только проценты**:
  ```bash
  python quest.py stats --view rel
  ```