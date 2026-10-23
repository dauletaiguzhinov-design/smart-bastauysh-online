(function () {
  "use strict";

  // Диагностика тақырыптары
  const topics = [
    "Қосу және азайту",
    "Көбейту және бөлу",
    "Мәтінді есеп"
  ];

  // Әр тапсырмада:
  // topic — тақырып нөмірі: 0, 1 немесе 2
  // level — күрделілік деңгейі: 1, 2 немесе 3

  const bank = [
    {
      id: 0,
      q: "240 + 130 = ?",
      answer: 370,
      topic: 0,
      level: 1,
      hint: "Жүздіктер мен ондықтарды бөлек қос."
    },
    {
      id: 1,
      q: "580 − 240 = ?",
      answer: 340,
      topic: 0,
      level: 1,
      hint: "Алдымен 200, содан кейін 40 азайт."
    },
    {
      id: 2,
      q: "368 + 257 = ?",
      answer: 625,
      topic: 0,
      level: 2,
      hint: "Бірліктерден баста. Ондыққа ауысуды ескер."
    },
    {
      id: 3,
      q: "704 − 286 = ?",
      answer: 418,
      topic: 0,
      level: 2,
      hint: "Разрядтан қарыз алу тәсілін қолдан."
    },
    {
      id: 4,
      q: "487 + 368 − 259 = ?",
      answer: 596,
      topic: 0,
      level: 3,
      hint: "Алдымен қосындыны, кейін айырманы тап."
    },
    {
      id: 5,
      q: "6 × 7 = ?",
      answer: 42,
      topic: 1,
      level: 1,
      hint: "6 санын 7 рет қосуға болады."
    },
    {
      id: 6,
      q: "48 ÷ 6 = ?",
      answer: 8,
      topic: 1,
      level: 1,
      hint: "6-ны қандай санға көбейтсең, 48 шығады?"
    },
    {
      id: 7,
      q: "(36 + 18) ÷ 6 = ?",
      answer: 9,
      topic: 1,
      level: 2,
      hint: "Алдымен жақша ішіндегі амалды орында."
    },
    {
      id: 8,
      q: "9 × 8 − 24 = ?",
      answer: 48,
      topic: 1,
      level: 2,
      hint: "Көбейту азайтудан бұрын орындалады."
    },
    {
      id: 9,
      q: "(72 ÷ 8 + 7) × 5 = ?",
      answer: 80,
      topic: 1,
      level: 3,
      hint: "Жақша ішінде алдымен бөлуді орында."
    },
    {
      id: 10,
      q: "3 қораптың әрқайсысында 6 қарындаш бар. Барлығы неше қарындаш?",
      answer: 18,
      topic: 2,
      level: 1,
      hint: "Қорап санын әр қораптағы қарындаш санына көбейт."
    },
    {
      id: 11,
      q: "20 алма 4 балаға тең бөлінді. Әр бала неше алма алды?",
      answer: 5,
      topic: 2,
      level: 1,
      hint: "Алма санын бала санына бөл."
    },
    {
      id: 12,
      q: "Бір дәптер 80 теңге. 4 дәптер үшін 500 теңге берілді. Қанша теңге қайтарылады?",
      answer: 180,
      topic: 2,
      level: 2,
      hint: "4 дәптердің құнын тап. Оны 500-ден азайт."
    },
    {
      id: 13,
      q: "Автобуста 32 адам болды. 8 адам түсіп, 5 адам мінді. Неше адам қалды?",
      answer: 29,
      topic: 2,
      level: 2,
      hint: "Түскен адамдарды азайтып, мінген адамдарды қос."
    },
    {
      id: 14,
      q: "5 қораптың әрқайсысында 8 кітап бар. 13 кітап оқушыларға берілді. Неше кітап қалды?",
      answer: 27,
      topic: 2,
      level: 3,
      hint: "Барлық кітап санын тап. Берілген кітаптарды азайт."
    }
  ];

  // Диагностикаға әр тақырыптан 3 тапсырма таңдаймыз.
  function diagnostic() {
    const ids = [0, 2, 3, 5, 7, 8, 10, 12, 13];

    return ids.map(function (id) {
      return bank.find(function (task) {
        return task.id === id;
      });
    });
  }

  // Әр тақырып бойынша нәтижені есептеу
  function analyze(answers) {
    return topics.map(function (name, topicIndex) {
      const rows = answers.filter(function (row) {
        const task = bank.find(function (item) {
          return item.id === row.id;
        });

        return task && task.topic === topicIndex;
      });

      const total = rows.length;

      const correct = rows.filter(function (row) {
        return row.correct === true;
      }).length;

      const percent = total > 0
        ? Math.round((correct / total) * 100)
        : 0;

      let level = 1;

      if (percent >= 80) {
        level = 3;
      } else if (percent >= 50) {
        level = 2;
      }

      return {
        name: name,
        topic: topicIndex,
        correct: correct,
        total: total,
        percent: percent,
        level: level
      };
    });
  }

  // Нәтижесіне сәйкес деңгейдегі тапсырмаларды таңдау
  function recommend(stats) {
    return stats.flatMap(function (result) {
      return bank.filter(function (task) {
        return (
          task.topic === result.topic &&
          task.level === result.level
        );
      });
    });
  }

  // Бұл функцияларды app.js файлы қолданады.
  window.Smart = {
    topics: topics,
    bank: bank,
    diagnostic: diagnostic,
    analyze: analyze,
    recommend: recommend
  };
})();