"use strict";

const view = document.querySelector("#view");

const levels = [
  "",
  "Қолдаумен бекіту",
  "Қолдану",
  "Күрделендіру"
];

let queue = [];
let answers = [];
let practiceAnswers = [];
let currentStats = [];
let position = 0;
let mode = "diagnostic";

// Басты бет
function home() {
  view.innerHTML = `
    <h2>Сәлем, жас зерттеуші!</h2>

    <p>
      Қосу мен азайту, көбейту мен бөлу және
      мәтінді есептер бойынша өзіңді тексер.
    </p>

    <p class="muted">
      Атыңды жазудың қажеті жоқ.
      Әр сұраққа санмен жауап бер.
      Асықпай ойлан — бұл тестке баға қойылмайды.
    </p>

    <button id="start">
      Диагностиканы бастау →
    </button>
  `;

  document.querySelector("#start").onclick = function () {
    queue = Smart.diagnostic();
    answers = [];
    practiceAnswers = [];
    currentStats = [];
    position = 0;
    mode = "diagnostic";
    showQuestion();
  };
}

// Бір сұрақты көрсету
function showQuestion() {
  const task = queue[position];

  const title = mode === "diagnostic"
    ? "ДИАГНОСТИКА"
    : "ЖЕКЕ ЖАТТЫҒУ";

  view.innerHTML = `
    <small>
      ${title} · ${position + 1} / ${queue.length}
    </small>

    <progress
      value="${position}"
      max="${queue.length}">
    </progress>

    <p>${Smart.topics[task.topic]}</p>

    <div class="question">${task.q}</div>

    <form id="answerForm">
      <label for="answer">Санмен жауап бер:</label>

      <input
        id="answer"
        type="number"
        step="1"
        required
        autocomplete="off">

      <br>

      <button type="submit">
        Жауапты қабылдау
      </button>
    </form>

    <div id="feedback"></div>
  `;

  document.querySelector("#answer").focus();

  document.querySelector("#answerForm").onsubmit = function (event) {
    event.preventDefault();

    const input = document.querySelector("#answer");
    const raw = input.value.trim();

    if (raw === "") {
      return;
    }

    const value = Number(raw);

    if (!Number.isFinite(value)) {
      return;
    }

    const row = {
      id: task.id,
      value: value,
      correct: value === task.answer
    };

    if (mode === "diagnostic") {
      answers.push(row);
    } else {
      practiceAnswers.push(row);
    }

    document.querySelector("#answerForm").hidden = true;

    const feedback = document.querySelector("#feedback");
    feedback.className = "feedback";

    if (mode === "diagnostic") {
      feedback.textContent = "Жауабың қабылданды!";
    } else {
      const message = row.correct
        ? "Дұрыс! Жарайсың!"
        : "Бірге тексерейік.";

      feedback.textContent =
        message + "\n" +
        task.hint + "\n" +
        "Дұрыс жауап: " + task.answer;
    }

    const next = document.createElement("button");

    next.textContent = position + 1 === queue.length
      ? "Нәтижені көру"
      : "Келесі сұрақ →";

    next.onclick = function () {
      position += 1;

      if (position < queue.length) {
        showQuestion();
      } else if (mode === "diagnostic") {
        currentStats = Smart.analyze(answers);
        showResults();
      } else {
        showPracticeResults();
      }
    };

    view.append(next);
    next.focus();
  };
}

// Тақырыптар бойынша нәтиже карточкалары
function makeTiles(stats) {
  return `
    <div class="grid">
      ${stats.map(function (item) {
        return `
          <div class="tile">
            <span>${item.name}</span>

            <strong>
              ${item.correct} / ${item.total}
            </strong>

            <div class="bar">
              <i style="width: ${item.percent}%"></i>
            </div>

            <p>${item.percent}% дұрыс</p>
            <p>${levels[item.level]}</p>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

// Диагностика нәтижесі
function showResults() {
  const correct = answers.filter(function (row) {
    return row.correct;
  }).length;

  view.innerHTML = `
    <h2>Сенің оқу картаң</h2>

    <p>
      Барлығы: <b>${answers.length}</b> сұрақ.
      Дұрыс жауап: <b>${correct}</b>.
    </p>

    ${makeTiles(currentStats)}

    <p class="muted">
      Әр тақырып бойынша:
      0–49% — қолдаумен бекіту;
      50–79% — қолдану;
      80–100% — күрделендіру.
    </p>

    <p class="muted">
      Бұл — алдын ала диагностика.
      Әр тақырыпта 3 сұрақ қана бар.
      Мұғалім нәтижені басқа жұмыстармен бірге қарайды.
    </p>

    <button id="practice">
      Маған арналған тапсырмалар →
    </button>

    <button id="download" class="secondary">
      Есепті жүктеу
    </button>

    <button id="restart" class="secondary">
      Қайта бастау
    </button>
  `;

  document.querySelector("#practice").onclick = function () {
    queue = Smart.recommend(currentStats);
    practiceAnswers = [];
    position = 0;
    mode = "practice";
    showQuestion();
  };

  document.querySelector("#download").onclick = downloadReport;
  document.querySelector("#restart").onclick = home;
}

// Жеке жаттығу нәтижесі
function showPracticeResults() {
  const correct = practiceAnswers.filter(function (row) {
    return row.correct;
  }).length;

  view.innerHTML = `
    <h2>Жаттығу аяқталды!</h2>

    <p>
      ${practiceAnswers.length} тапсырманың
      ${correct} жауабы дұрыс.
    </p>

    <div class="feedback">
      Еңбегің үшін рақмет!
      Қате кеткен есептердің шешу тәсілін қайтала.
    </div>

    <p class="muted">
      Жаттығуда диагностикадағы кейбір есептер
      қайталануы мүмкін. Сондықтан бұл нәтиже
      білім өсімінің тәуелсіз өлшемі болып саналмайды.
    </p>

    <button id="back">
      Оқу картасына оралу
    </button>

    <button id="download" class="secondary">
      Есепті жүктеу
    </button>
  `;

  document.querySelector("#back").onclick = showResults;
  document.querySelector("#download").onclick = downloadReport;
}

// Нәтижені файлға жүктеу
function downloadReport() {
  const report = {
    project: "Smart Бастауыш AI",
    date: new Date().toISOString(),
    grade: 3,
    subject: "Математика",
    diagnostic: currentStats,
    diagnosticAnswers: answers,
    practiceAnswers: practiceAnswers,
    note: "Алдын ала диагностика. Мұғалім тексеруі қажет."
  };

  const text = JSON.stringify(report, null, 2);

  const file = new Blob([text], {
    type: "application/json;charset=utf-8"
  });

  const url = URL.createObjectURL(file);
  const link = document.createElement("a");

  link.href = url;
  link.download = "smart-report.json";

  document.body.append(link);
  link.click();
  link.remove();

  setTimeout(function () {
    URL.revokeObjectURL(url);
  }, 1000);
}

// Мұғалімге арналған бөлім
function showTeacher() {
  view.innerHTML = `
    <h2>Мұғалімге арналған ақпарат</h2>

    <p>
      Оқушы 9 сұрақ орындайды.
      Жүйе әр тақырыптың нәтижесін бөлек есептеп,
      сәйкес деңгейдегі тапсырмалар ұсынады.
    </p>

    <table>
      <thead>
        <tr>
          <th>Нәтиже</th>
          <th>Ұсынылатын жұмыс</th>
        </tr>
      </thead>

      <tbody>
        <tr>
          <td>0–49%</td>
          <td>Негізгі дағдыны қолдаумен бекіту</td>
        </tr>
        <tr>
          <td>50–79%</td>
          <td>Білімді қолдануға арналған тапсырмалар</td>
        </tr>
        <tr>
          <td>80–100%</td>
          <td>Күрделендірілген тапсырмалар</td>
        </tr>
      </tbody>
    </table>

    <p class="muted">
      Бұл шектер — жобаның әдістемелік таңдауы.
      Ресми бағалау нормасы емес.
      Тапсырмаларды өз оқу бағдарламаңызбен
      салыстырып тексеріңіз.
    </p>

    <h3>Деректерді қорғау</h3>

    <p>
      Оқушының аты-жөні сұралмайды.
      Нәтижелер осы бет ашық тұрған кезде ғана
      жадта сақталады. Бетті жаңартқанда жойылады.
      Жүктелген есеп файлы компьютерде қалады.
    </p>

    <h3>ЖИ туралы</h3>

    <p>
       Диагностика нәтижесін есептеу және тапсырмаларды таңдау
      ережелерге негізделген. Жергілікті ЖИ моделі мұғалімге
      түсіндірме жобасын дайындайды. Мұғалім жауапты тексеріп, түзетеді.
    </p>

    <button id="return">Оқушы бөліміне оралу</button>
  `;

  document.querySelector("#return").onclick = openStudent;
}

// Аяқталған нәтижеге немесе ағымдағы сұраққа оралу
function openStudent() {
  aiPanel.hidden = true;
  if (queue.length > 0 && position < queue.length) {
    showQuestion();
  } else if (currentStats.length > 0) {
    showResults();
  } else {
    home();
  }
}

document.querySelector("#tabStart").onclick = openStudent;
document.querySelector("#tabTeacher").onclick = showTeacher;

// Қолданбаны ашу
home();
// ЖИ көмекшісінің жеке бөлімі
const aiPanel = document.createElement("section");

aiPanel.className = "card";
aiPanel.style.marginTop = "24px";

aiPanel.innerHTML = `
  <h2>✦ ЖИ түсіндірме көмекшісі</h2>

  <p>
    Қайталағың келетін тақырыпты таңда.
    ЖИ оны мысалмен түсіндіруге көмектеседі.
  </p>

  <label for="aiTopic">Тақырып:</label>

  <select id="aiTopic">
    <option value="0">Қосу және азайту</option>
    <option value="1">Көбейту және бөлу</option>
    <option value="2">Мәтінді есеп</option>
  </select>

  <br>

  <button id="askAI">
    ЖИ түсіндірмесін сұрау
  </button>

  <p class="muted">
    ЖИ жауабында тілдік немесе математикалық
    қателер болуы мүмкін. Мұғалім тексеруі қажет.
  </p>

  <div
    id="aiAnswer"
    class="feedback"
    role="status"
    aria-live="polite">
    Түсіндірме осы жерде көрсетіледі.
  </div>
`;

const footer = document.querySelector("main footer");
footer.before(aiPanel);

// ЖИ-ге тек таңдалған тақырып жіберіледі
document.querySelector("#askAI").onclick = async function () {
  const button = document.querySelector("#askAI");
  const output = document.querySelector("#aiAnswer");
  const select = document.querySelector("#aiTopic");

  const topic = Smart.topics[Number(select.value)];

  button.disabled = true;
  select.disabled = true;
  output.textContent = "ЖИ түсіндірме дайындауда…";

  const controller = new AbortController();

  const timer = setTimeout(function () {
    controller.abort();
  }, 125000);

  try {
    const response = await fetch("/api/explain", {
      method: "POST",

      headers: {
        "Content-Type": "application/json"
      },

      body: JSON.stringify({
        topic: topic
      }),

      signal: controller.signal
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(
        result.error || "ЖИ сұрауын орындау мүмкін болмады."
      );
    }

    if (
      typeof result.text !== "string" ||
      !result.text.trim()
    ) {
      throw new Error("ЖИ бос жауап қайтарды.");
    }

    // ЖИ мәтінін HTML ретінде орындамаймыз
    output.textContent =
      result.text + "\n\n" +
      (result.source || "ЖИ жауабы. Мұғалім тексеруі қажет.");

  } catch (error) {
    if (error.name === "AbortError") {
      output.textContent =
        "Күту уақыты аяқталды. Біраздан кейін қайта көріңіз.";
    } else {
      output.textContent =
        "Түсіндірме алынбады. " + error.message;
    }

  } finally {
    clearTimeout(timer);
    button.disabled = false;
    select.disabled = false;
  }
};
aiPanel.hidden = true;

document.getElementById("tabTeacher").addEventListener("click", () => {
  aiPanel.hidden = false;
});

document.getElementById("tabStart").addEventListener("click", () => {
  aiPanel.hidden = true;
});
aiPanel.querySelector("h2").textContent =
  "ЖИ көмекшісі — мұғалімге арналған";

aiPanel.querySelector("p").textContent =
  "Тақырыпты таңдап, түсіндірме жобасын алыңыз. " +
  "Оқушыға ұсынар алдында тілін және есептеулерін тексеріп, түзетіңіз.";
  const reviewBlock = document.createElement("div");

reviewBlock.innerHTML = `
  <h3>Түсіндірмені өңдеу</h3>
  <p>ЖИ жауабын көшіріп алып, тілін және есептеулерін түзетіңіз.</p>

  <button id="copyToEditor" type="button">
    Жауапты өңдеу өрісіне көшіру
  </button>

  <label for="teacherExplanation">Мұғалім түзететін мәтін:</label>
  <textarea
    id="teacherExplanation"
    rows="8"
    style="width:100%; box-sizing:border-box; margin-top:8px;"
  ></textarea>
`;

aiPanel.append(reviewBlock);

document.getElementById("copyToEditor").onclick = () => {
  const editor = document.getElementById("teacherExplanation");
  editor.value = document.getElementById("aiAnswer").textContent;
  editor.focus();
};
const approvedCard = document.createElement("section");
approvedCard.className = "card";
approvedCard.style.marginTop = "24px";
approvedCard.hidden = true;

const approvedTitle = document.createElement("h2");
approvedTitle.textContent = "Мұғалім тексерген түсіндірме";

const approvedText = document.createElement("p");
approvedText.style.whiteSpace = "pre-wrap";

approvedCard.append(approvedTitle, approvedText);
aiPanel.after(approvedCard);

const approveButton = document.createElement("button");
approveButton.type = "button";
approveButton.textContent = "Тексердім — оқушыға көрсету";
reviewBlock.append(approveButton);

approveButton.onclick = () => {
  const text = document.getElementById("teacherExplanation").value.trim();

  if (!text) {
    alert("Алдымен түсіндірме мәтінін енгізіңіз.");
    return;
  }

  approvedText.textContent = text;
  approvedCard.hidden = false;
};
let currentStudent = null;

async function authRequest(path, data) {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(data)
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.error || "Сұрау орындалмады.");
  }

  return result;
}
const authCard = document.createElement("section");
authCard.className = "card";
authCard.style.marginBottom = "24px";

authCard.innerHTML = `
  <h2>Оқушы кабинеті</h2>
  <p>Аты-жөніңнің орнына өзің таңдаған логинді қолдан.</p>

  <form id="studentAuthForm">
    <label for="studentLogin">Логин</label>
    <input
      id="studentLogin"
      type="text"
      minlength="3"
      maxlength="24"
      pattern="[a-zA-Z0-9_]{3,24}"
      autocomplete="username"
      required
    >
    <p>3–24 таңба: латын әріптері, сандар немесе _ белгісі.</p>

    <label for="studentPassword">Құпиясөз</label>
    <input
      id="studentPassword"
      type="password"
      minlength="10"
      maxlength="128"
      autocomplete="current-password"
      required
    >
    <p>Құпиясөз кемінде 10 таңбадан тұрсын.</p>

    <button type="submit" value="login">Кіру</button>
    <button type="submit" value="register">Тіркелу</button>
  </form>

  <p id="authMessage" role="status"></p>
`;

view.before(authCard);
document.querySelector("#studentAuthForm")
  .addEventListener("submit", async (event) => {
    event.preventDefault();

    const form = event.currentTarget;
    const message = document.querySelector("#authMessage");
    const action = event.submitter?.value || "login";

    const login = document.querySelector("#studentLogin").value;
    const password = document.querySelector("#studentPassword").value;
    const buttons = form.querySelectorAll("button");

    buttons.forEach((button) => button.disabled = true);
    message.textContent = "Күте тұрыңыз...";

    try {
      const result = await authRequest(`/api/${action}`, {
        login,
        password
      });

      currentStudent = result.student;
      form.reset();
      form.hidden = true;

      message.textContent =
        `Қош келдің, ${currentStudent.login}!`;
    } catch (error) {
      message.textContent = error.message;
    } finally {
      buttons.forEach((button) => button.disabled = false);
    }
  });
  async function restoreStudentSession() {
  const message = document.querySelector("#authMessage");
  const form = document.querySelector("#studentAuthForm");

  try {
    const response = await fetch("/api/me", {
      cache: "no-store"
    });

    if (!response.ok) {
      throw new Error("Аккаунтты тексеру орындалмады.");
    }

    const result = await response.json();
    currentStudent = result.student;

    form.hidden = Boolean(currentStudent);
    message.textContent = currentStudent
      ? `Қош келдің, ${currentStudent.login}!`
      : "";
  } catch (error) {
    message.textContent = "Сервермен байланысты тексеріңіз.";
  }
}

restoreStudentSession();
const logoutButton = document.createElement("button");
logoutButton.type = "button";
logoutButton.textContent = "Аккаунттан шығу";
authCard.append(logoutButton);

logoutButton.addEventListener("click", async () => {
  logoutButton.disabled = true;

  try {
    await authRequest("/api/logout", {});
    window.location.reload();
  } catch (error) {
    document.querySelector("#authMessage").textContent =
      error.message;
    logoutButton.disabled = false;
  }
});