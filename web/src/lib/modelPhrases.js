import {
  Activity,
  Atom,
  Ban,
  Binary,
  Brain,
  Bug,
  Coffee,
  Coins,
  Cpu,
  Crown,
  Ear,
  Eye,
  Flag,
  Flame,
  Gamepad2,
  Hourglass,
  Infinity,
  Orbit,
  PackageCheck,
  TreePalm,
  PartyPopper,
  RefreshCw,
  Rocket,
  Smile,
  Snowflake,
  Sparkles,
  ThumbsUp,
  Trees,
  TriangleAlert,
  WandSparkles,
  Wind,
  Wrench,
} from "lucide-react";

export const MODEL_PHRASES = [
  { text: "Щас всё взлетит, только провода прикурите!", icon: Rocket },
  { text: "Модель думает, кофе остывает, ждите чуда.", icon: Coffee },
  { text: "Процесс пошёл — либо результат, либо фейерверк!", icon: PartyPopper },
  { text: "Ядро греется, логика плавится — ответ родится!", icon: Flame },
  { text: "Система считает, вселенная ждёт...", icon: Orbit },
  { text: "Ничего не трогайте! Я сам всё сломаю!", icon: Ban },
  { text: "Обработка идёт — молитесь процессору.", icon: Cpu },
  { text: "Код компилится, реальность искажается...", icon: Binary },
  { text: "Запускаю! Если зависнет — перезагрузка мира.", icon: Atom },
  { text: "Алгоритм пыхтит, данные танцуют — щас выдаст!", icon: Activity },
  { text: "Вжух — и будет магия. Или ошибка. Посмотрим.", icon: WandSparkles },
  { text: "Симуляция началась — удачи нам всем.", icon: Gamepad2 },
  { text: "Машина шевелит нейронами — не мешайте!", icon: Brain },
  { text: "Всё просчитаю, звезды сложу — ответ принесу.", icon: Sparkles },
  { text: "Погнали! Но без гарантий, я предупредил.", icon: TriangleAlert },
  { text: "Тихо! Слышите? Это думает ваш компьютер.", icon: Ear },
  { text: "Запрос ушёл в бесконечность. Ждите ответа...", icon: Infinity },
  { text: "Пока модель грузится, успейте выдохнуть.", icon: Wind },
  { text: "Секундочку, настраиваю кривизну пространства...", icon: Orbit },
  { text: "Готово! Почти. Ладно, не почти. Сейчас.", icon: Hourglass },
];

export const DONE_PHRASES = [
  { text: "Готово! Я же говорил, что я гений!", icon: Crown },
  { text: "Всё! Можете выдохнуть и похвалить меня.", icon: ThumbsUp },
  { text: "Результат есть! Претензии принимаются в письменном виде.", icon: PackageCheck },
  { text: "Готово! Если что-то не так — это баг, а не фича.", icon: Bug },
  { text: "Вуаля! Магия закончилась, началась реальность.", icon: WandSparkles },
  { text: "Готово! Можете забрать, только аккуратно, горячее!", icon: Flame },
  { text: "Всё посчитал, всё решил. Кто сомневался — идите лесом.", icon: Trees },
  { text: "Готово! Если результат не нравится — пересчитаю за двойную плату.", icon: Coins },
  { text: "Финиш! Компьютер выжил, я молодец.", icon: Flag },
  { text: "Готово! Можете проверять, но я уже ушёл пить кофе.", icon: Coffee },
  { text: "Всё! Модель отработала, мозги остывают.", icon: Snowflake },
  { text: "Готово! Смотрите, любуйтесь, но в код не лезьте!", icon: Eye },
  { text: "Результат получен! Жалобы принимаются до конца света.", icon: Smile },
  { text: "Готово! Если зависло — перезагрузите себя, а не комп.", icon: RefreshCw },
  { text: "Всё сделано! Остальное — уже ваши проблемы.", icon: Wrench },
  { text: "Готово! Я старался, честно. Почти.", icon: Sparkles },
  { text: "Вуаля! Даже я удивлён, что сработало.", icon: PartyPopper },
  { text: "Готово! Теперь можно праздновать или плакать — по ситуации.", icon: PartyPopper },
  { text: "Всё! Миссия выполнена, процессор в отпуск.", icon: TreePalm },
  { text: "Готово! Если не нравится — переделайте сами!", icon: Wrench },
];

export function shufflePhrases(items, excludeText) {
  const deck = items.slice();
  for (let i = deck.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    const tmp = deck[i];
    deck[i] = deck[j];
    deck[j] = tmp;
  }
  if (excludeText && deck.length > 1 && deck[0].text === excludeText) {
    const swap = deck.findIndex((item) => item.text !== excludeText);
    if (swap > 0) {
      const tmp = deck[0];
      deck[0] = deck[swap];
      deck[swap] = tmp;
    }
  }
  return deck;
}

export function pickPhrase(items) {
  return items[Math.floor(Math.random() * items.length)];
}
