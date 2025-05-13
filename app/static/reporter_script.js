function showFiles(version, files) {
  const reportList = document.getElementById("report-list");
  const reportDetails = document.getElementById("report-details");
  reportList.innerHTML = "";
  reportDetails.innerHTML = "";

  files.sort((a, b) => b.localeCompare(a)); // descendente

  files.forEach(file => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.textContent = file;
    btn.onclick = () => {
      fetch(`/reports/${version}/${file}`)
        .then(res => res.json())
        .then(data => {
          reportDetails.innerHTML = "";
          data.forEach(entry => {
            const div = document.createElement("div");
            div.className = "entry";
            div.innerHTML = `
              <h3>${entry.class}</h3>
              <p>Train: ${entry.train_count} (${entry.train_status})</p>
              <p>Validation: ${entry.validation_count} (${entry.validation_status})</p>
            `;
            reportDetails.appendChild(div);
          });
        });
    };
    li.appendChild(btn);
    reportList.appendChild(li);
  });
}

fetch("/reports/index.json")
  .then(res => res.json())
  .then(indexData => {
    const versionList = document.getElementById("version-list");
    Object.keys(indexData).forEach(ver => {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.textContent = ver;
      btn.onclick = () => showFiles(ver, indexData[ver]);
      li.appendChild(btn);
      versionList.appendChild(li);
    });
  });
