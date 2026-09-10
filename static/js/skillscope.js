/* ==========================================================================
   SkillScope - the small amount of JavaScript the site needs.

   Three jobs, all of them about telling somebody what is happening:

     1. Busy buttons   - a form that has been submitted says so, and cannot be
                         submitted twice by an impatient double-click.
     2. Upload progress - a 100 MB recorded lecture takes a while. Without a
                         bar, people assume it has frozen and reload, which
                         loses the upload.
     3. File chosen    - the default file input tells you nothing useful, and
                         the size limit is easier to obey before uploading
                         than after being rejected.

   Nothing here is required for the site to work. If JavaScript is off, every
   form still submits normally -- this only adds feedback.
   ========================================================================== */

(function () {
  "use strict";

  var MAX_MB = Number(document.body.dataset.maxUploadMb || 100);

  /* ---------------------------------------------------------------------
     1 + 2. Submitting a form
     --------------------------------------------------------------------- */

  function busyMarkup(label) {
    return '<span class="ss-spinner" aria-hidden="true"></span>' + label;
  }

  function handleSubmit(form) {
    // Let the browser's own required-field check run first. If it failed,
    // the form is not actually going anywhere, so do not show a busy state.
    if (typeof form.checkValidity === "function" && !form.checkValidity()) {
      return;
    }

    var button = form.querySelector('button[type="submit"], input[type="submit"]');
    if (button) {
      if (button.dataset.busy === "1") { return; }
      button.dataset.busy = "1";
      button.dataset.originalHtml = button.innerHTML;
      button.innerHTML = busyMarkup(button.dataset.busyLabel || "Working...");
      button.disabled = true;

      // A disabled button is not submitted with the form, so if this button
      // carried a name and value (verify / reject, for instance) put it back
      // as a hidden field or the server would not know which was pressed.
      if (button.name) {
        var hidden = document.createElement("input");
        hidden.type = "hidden";
        hidden.name = button.name;
        hidden.value = button.value;
        form.appendChild(hidden);
      }
    }

    var fileInput = form.querySelector('input[type="file"]');
    var hasFile = fileInput && fileInput.files && fileInput.files.length > 0;
    if (hasFile) {
      showUploadProgress(form, fileInput.files[0]);
    }
  }

  function showUploadProgress(form, file) {
    var wrap = document.createElement("div");
    wrap.className = "ss-upload";
    wrap.innerHTML =
      '<div class="ss-upload-head">' +
        '<span class="ss-upload-name"></span>' +
        '<span class="ss-upload-pct">0%</span>' +
      "</div>" +
      '<div class="ss-progress"><div class="ss-progress-bar" style="width:0%"></div></div>' +
      '<div class="ss-upload-note">Uploading. Please keep this page open.</div>';
    wrap.querySelector(".ss-upload-name").textContent =
      file.name + " (" + formatSize(file.size) + ")";
    form.appendChild(wrap);

    var bar = wrap.querySelector(".ss-progress-bar");
    var pct = wrap.querySelector(".ss-upload-pct");
    var note = wrap.querySelector(".ss-upload-note");

    // The form posts normally; this reads real progress from a parallel
    // XHR-free source is not possible, so instead we submit through XHR and
    // let the browser follow the response.
    var xhr = new XMLHttpRequest();
    xhr.open(form.method || "POST", form.action, true);
    xhr.upload.addEventListener("progress", function (e) {
      if (!e.lengthComputable) { return; }
      var done = Math.round((e.loaded / e.total) * 100);
      bar.style.width = done + "%";
      pct.textContent = done + "%";
      if (done >= 100) {
        note.textContent = "Upload finished. Saving...";
      }
    });
    xhr.addEventListener("load", function () {
      // Replace the page with whatever came back, exactly as a normal form
      // post would have done.
      document.open();
      document.write(xhr.responseText);
      document.close();
    });
    xhr.addEventListener("error", function () {
      note.textContent = "The upload failed. Check your connection and try again.";
      note.classList.add("is-error");
      bar.classList.add("is-error");
      resetButtons(form);
    });
    xhr.send(new FormData(form));

    // We are sending it ourselves, so stop the browser sending it as well.
    form.dataset.xhrSubmitted = "1";
  }

  function resetButtons(form) {
    form.querySelectorAll("button[data-busy]").forEach(function (button) {
      button.disabled = false;
      button.dataset.busy = "";
      if (button.dataset.originalHtml) {
        button.innerHTML = button.dataset.originalHtml;
      }
    });
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!(form instanceof HTMLFormElement) || form.dataset.noBusy === "1") { return; }

    var fileInput = form.querySelector('input[type="file"]');
    var hasFile = fileInput && fileInput.files && fileInput.files.length > 0;

    handleSubmit(form);

    // An upload is sent by XHR above, so the normal submit must be cancelled.
    if (hasFile && form.dataset.xhrSubmitted === "1") {
      event.preventDefault();
    }
  });

  /* ---------------------------------------------------------------------
     3. Choosing a file
     --------------------------------------------------------------------- */

  function formatSize(bytes) {
    if (bytes < 1024) { return bytes + " B"; }
    if (bytes < 1024 * 1024) { return Math.round(bytes / 1024) + " KB"; }
    return (bytes / 1024 / 1024).toFixed(1) + " MB";
  }

  document.addEventListener("change", function (event) {
    var input = event.target;
    if (input.type !== "file" || !input.files || !input.files.length) { return; }

    var file = input.files[0];
    var note = input.parentNode.querySelector(".ss-file-note");
    if (!note) {
      note = document.createElement("div");
      note.className = "ss-file-note";
      input.parentNode.appendChild(note);
    }

    var tooBig = file.size > MAX_MB * 1024 * 1024;
    note.textContent = tooBig
      ? file.name + " is " + formatSize(file.size) + " - larger than the "
        + MAX_MB + " MB limit. Choose a smaller file."
      : file.name + " - " + formatSize(file.size) + ", ready to upload.";
    note.classList.toggle("is-error", tooBig);

    // Stop the submit before a long upload that the server would only reject
    // at the far end.
    var form = input.form;
    if (form) {
      var button = form.querySelector('button[type="submit"]');
      if (button) { button.disabled = tooBig; }
    }
  });

  /* ---------------------------------------------------------------------
     Dismissable alerts
     --------------------------------------------------------------------- */

  document.addEventListener("click", function (event) {
    var close = event.target.closest("[data-dismiss-alert]");
    if (close) { close.closest(".alert").remove(); }
  });
})();
