(() => {
  const token = document.querySelector('meta[name="studio-token"]').content;
  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  let activeRunId = null;
  let timer = null;

  async function api(path, method = "GET", body) {
    const response = await fetch(path, {
      method,
      headers: {"Content-Type":"application/json","X-Studio-Token":token},
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    return data;
  }

  function toast(message, error = false) {
    const node = $("toast"); node.textContent = message; node.classList.remove("hidden","error");
    if (error) node.classList.add("error");
    setTimeout(() => node.classList.add("hidden"), 4200);
  }

  function statusLabel(status) {
    return ({ANALYZING:"Codex đang phân tích",DRAFT_READY:"DRAFT · chờ bạn duyệt",PLAN_APPROVED:"Storyboard đã duyệt",MANIFEST_DRAFT:"Manifest DRAFT",MANIFEST_APPROVED:"Đã duyệt giới hạn",SUBMITTED:"Đã gửi Muse",RUNNING:"Muse đang tạo video",POLL_ERROR:"Lỗi khi kiểm tra task",MEDIA_READY:"Clip đã QC",QC_WARN:"QC cần xem lại",REVIEW_READY:"Codex đã đề xuất continuity",REVIEWED:"Continuity đã xác nhận",EXPORTED:"Đã xuất tập",EXPORT_QC_WARN:"File xuất cần QC",FAILED:"Có lỗi"})[status] || status;
  }

  function badgeClass(status) {
    if (["MEDIA_READY","REVIEWED","EXPORTED","PLAN_APPROVED","MANIFEST_APPROVED"].includes(status)) return "good";
    if (["QC_WARN","EXPORT_QC_WARN","POLL_ERROR"].includes(status)) return "warn";
    if (status === "FAILED") return "fail";
    return "";
  }

  function updateStepper(status, hasYouTubeMetadata = false) {
    const active = status === "ANALYZING" || status === "FAILED" ? 1 : status === "DRAFT_READY" ? 2 :
      ["PLAN_APPROVED","MANIFEST_DRAFT","MANIFEST_APPROVED","SUBMITTED","RUNNING"].includes(status) ? 3 :
      ["MEDIA_READY","QC_WARN","REVIEW_READY","REVIEWED"].includes(status) ? 4 :
      status === "EXPORTED" && hasYouTubeMetadata ? 6 : status.startsWith("EXPORT") || status === "EXPORTED" ? 5 : 1;
    document.querySelectorAll(".flow-step").forEach((el,i) => { el.classList.toggle("active",i===active);el.classList.toggle("done",i<active); });
  }

  async function loadHealth() {
    try {
      const data = await api("/api/health");
      const codex = $("codex-health"); codex.querySelector("span").textContent="Codex"; codex.title=data.llm_backend||"Configure OPENAI_API_KEY or GEMINI_API_KEY for API fallback"; codex.classList.toggle("ok",data.codex_available);codex.classList.toggle("bad",!data.codex_available);codex.querySelector("b").textContent=data.codex_available?(data.llm_backend || "Sẵn sàng"):"Chưa sẵn sàng";
      const gateway = $("gateway-health"); const connected=!!data.gateway.connected;gateway.classList.toggle("ok",connected);gateway.classList.toggle("bad",!connected);gateway.querySelector("b").textContent=connected?"Đã kết nối":"Chưa kết nối";
      gateway.title=connected?(data.gateway.models||[]).join(", "):data.gateway.detail||"";
    } catch (_) { $("codex-health").classList.add("bad");$("gateway-health").classList.add("bad"); }
  }

  async function loadRuns() {
    try {
      const runs = await api("/api/runs");
      $("run-list").innerHTML = runs.length ? runs.map((run) => `<button class="run-item ${run.run_id===activeRunId?'active':''}" data-run="${esc(run.run_id)}"><strong>${esc(run.title)}</strong><small>${esc(statusLabel(run.status))} · ${new Date(run.updated_at).toLocaleDateString()}</small></button>`).join("") : '<div class="muted pad">Chưa có dự án mới</div>';
      document.querySelectorAll("[data-run]").forEach((el) => el.addEventListener("click", () => selectRun(el.dataset.run)));
    } catch (_) {}
  }

  async function selectRun(id) {
    activeRunId = id;
    $("new-view").classList.add("hidden"); $("run-view").classList.remove("hidden");
    await refreshRun(); await loadRuns();
    if (timer) clearInterval(timer);
    timer = setInterval(() => { if (activeRunId===id) refreshRun(true); }, 3000);
  }

  function planHtml(run) {
    const p=run.analysis; if(!p) return "";
    const shots=p.episode.shots.slice().sort((a,b)=>a.order-b.order);
    const cards=shots.map((s)=>`<article class="shot-card"><h3><span>${esc(s.shot_id)} · ${esc(s.planned_duration_seconds)}s</span><span class="status-tag">${esc(s.continuity_level)}</span></h3><p>${esc(s.purpose)}</p><small>${esc(s.characters_on_screen.join(", "))} · ${esc(s.camera.shot_size)} · ${esc(s.camera.movement)}</small><details class="shot-details"><summary>Xem storyboard, trạng thái và QA</summary><div class="detail-columns"><div><h4>Start state</h4><pre>${esc(JSON.stringify(s.start_state,null,2))}</pre></div><div><h4>End state</h4><pre>${esc(JSON.stringify(s.end_state,null,2))}</pre></div></div><h4>Action beats</h4><pre>${esc(JSON.stringify(s.action_beats,null,2))}</pre><div class="detail-columns"><div><h4>Camera & audio</h4><pre>${esc(JSON.stringify({camera:s.camera,lighting:s.lighting,audio:s.audio},null,2))}</pre></div><div><h4>References & QA</h4><pre>${esc(JSON.stringify({reference_plan:s.reference_plan,references:s.references,qa_checks:s.qa_checks,negative_constraints:s.negative_constraints,depends_on:s.depends_on},null,2))}</pre></div></div></details></article>`).join("");
    const characterCards=p.character_bibles.map((c)=>`<article class="shot-card"><h3>${esc(c.canonical_name)} <span class="status-tag">${esc(c.character_id)}</span></h3><p>${esc(c.role)} · ${esc(c.story_function)}</p><pre>${esc(JSON.stringify({identity_facts:c.identity_facts,continuity_locks:c.continuity_locks,costumes:c.costumes},null,2))}</pre></article>`).join("");
    const locations=p.world_bible.locations.map((l)=>`<article class="shot-card"><h3>${esc(l.canonical_name)} <span class="status-tag">${esc(l.location_id)}</span></h3><p>${esc(l.geography)}</p><pre>${esc(JSON.stringify({fixed_landmarks:l.fixed_landmarks,time_of_day:l.time_of_day,weather:l.weather,lighting_lock:l.lighting_lock,palette_lock:l.palette_lock},null,2))}</pre></article>`).join("");
    const props=p.world_bible.props.map((prop)=>`<article class="shot-card"><h3>${esc(prop.canonical_name)} <span class="status-tag">${esc(prop.prop_id)}</span></h3><p>${esc(prop.appearance)}</p><small>${esc(prop.initial_owner)} · ${esc(prop.state_rules.join(" · "))}</small></article>`).join("");
    return `<div class="summary-box"><h3>LOGLINE</h3><p>${esc(p.logline)}</p></div><div class="summary-box"><h3>TÓM TẮT</h3><p>${esc(p.synopsis)}</p></div><div class="manifest-grid"><div class="metric"><small>Dự án</small><strong>${esc(p.project_title)}</strong></div><div class="metric"><small>Thể loại</small><strong>${esc(p.genre)}</strong></div><div class="metric"><small>Phong cách</small><strong>${esc(p.visual_style)}</strong></div><div class="metric"><small>Storyboard</small><strong>${shots.length} shot · ${esc(p.episode.aspect_ratio)}</strong></div></div><h3 class="subhead">Character & World Bible · DRAFT</h3><div class="shot-grid">${characterCards}${locations}${props}</div><h3 class="subhead">Storyboard DRAFT</h3><div class="shot-grid">${cards}</div>${p.codex_notes?.length?`<div class="notice"><strong>Codex lưu ý:</strong> ${p.codex_notes.map(esc).join(" · ")}</div>`:""}`;
  }

  function shotSelector(run) {
    const shots=run.analysis?.episode?.shots||[];
    return `<label class="field"><span>Shot cần tạo tiếp theo</span><select id="shot-select">${shots.map((s)=>`<option value="${esc(s.shot_id)}" ${s.shot_id===run.selected_shot_id?'selected':''} ${s.status!=="APPROVED"?'disabled':''}>${esc(s.shot_id)} · ${esc(s.purpose)}</option>`).join("")}</select></label>`;
  }

  function manifestHtml(run) {
    const m=run.manifest_summary||{};
    return `<div class="manifest-grid"><div class="metric"><small>Manifest</small><strong class="code">${esc(m.manifest_id)}</strong></div><div class="metric"><small>Provider</small><strong>${esc(m.provider)}</strong></div><div class="metric"><small>Shot / thời lượng</small><strong>${esc(m.shot_id)} · ${esc(m.duration_seconds)}s</strong></div><div class="metric"><small>Request / reference</small><strong>${esc(m.request_count)} · ${esc(m.reference_count)}</strong></div></div><div class="notice">Đọc prompt và tham số trước khi duyệt. Bước kế tiếp chỉ lưu budget; chưa gửi request.</div><pre class="prompt-preview">${esc(m.prompt)}</pre><div class="inline-form"><label class="field"><span>Cơ sở usage (ghi đúng điều bạn đã đo/biết)</span><input id="usage-estimate" value="${esc(`${m.request_count||1} Muse video request; ${m.duration_seconds||0}s; ${m.aspect_ratio||'16:9'}; ${m.reference_count||0} references`)}"></label><label class="field"><span>Giới hạn tối đa</span><input id="budget-limit" value="Tối đa 1 request cho manifest này; không retry tự động"></label><label class="field"><span>Người duyệt</span><input id="approved-by" value="AnhTruong"></label></div><div class="panel-actions"><button class="primary-button" id="approve-budget">Duyệt usage và giới hạn</button></div>`;
  }

  function mediaHtml(run) {
    if(!run.media_path) return "";
    const sourceUrl=`/api/runs/${encodeURIComponent(run.run_id)}/video/source`;
    const masterUrl=run.conformed_media_path?`/api/runs/${encodeURIComponent(run.run_id)}/video/master`:sourceUrl;
    const meta=run.media_metadata||{};
    const check=run.qc_report?.status||"not run";
    const qc=run.qc_report?.checks||{};
    return `<div class="media-box"><video controls preload="metadata" src="${masterUrl}"></video><div class="media-meta"><span>Gốc ${esc(meta.width)}×${esc(meta.height)} · ${esc(meta.fps)}fps</span><span>${esc(meta.duration_seconds)}s</span><span>H.264 / AAC</span><span>QC master: ${esc(check)}</span><a href="${sourceUrl}" target="_blank">Video gốc</a></div></div>${run.conformed_media_path?`<div class="notice">Bản xem phía trên đã conform theo profile xuất. Nếu nguồn Muse có độ phân giải thấp hơn, upscale không tạo thêm chi tiết.</div>`:""}${run.qc_report?`<div class="manifest-grid">${Object.entries(qc).map(([k,v])=>`<div class="metric"><small>${esc(k.replaceAll('_',' '))}</small><strong>${v?"PASS":"WARN"}</strong></div>`).join("")}</div>`:""}<div class="frames">${["first","middle","last"].map((x)=>`<figure><img loading="lazy" src="/api/runs/${encodeURIComponent(run.run_id)}/frame/${x}" alt="${x} frame"><figcaption>${x.toUpperCase()} FRAME</figcaption></figure>`).join("")}</div>`;
  }

  function autopilotHtml(run) {
    if (!run.brief?.autopilot) return "";
    const labels={analyzing:"Planning storyboard",approving_storyboard:"Approving storyboard",preparing_manifest:"Preparing shot manifest",submitting_to_muse:"Submitting to Muse",polling_muse:"Generating video",extracting_frames_and_qc:"Extracting frames and running QC",reviewing_continuity:"Reviewing continuity",rendering_episode:"Rendering MP4",completed:"Complete",export_qc_warn:"Exported; final QC needs review",failed:"Stopped after an error"};
    const plannedCount=Number(run.autopilot_shot_count||run.analysis?.episode?.shots?.length||0);
    const count=Math.max(1,plannedCount);
    const index=Math.max(0,Number(run.autopilot_shot_index||0));
    const stage=run.autopilot_stage||"analyzing";
    const fraction={analyzing:0.03,approving_storyboard:0.08,preparing_manifest:0.12,submitting_to_muse:0.2,polling_muse:0.48,extracting_frames_and_qc:0.72,reviewing_continuity:0.9,rendering_episode:0.96,completed:1,export_qc_warn:1,failed:Math.max(0.08,index/count)}[stage]??0.05;
    const percent=Math.round(Math.max(4,Math.min(100,((Math.max(0,index-1)+fraction)/count)*100)));
    const shot=run.autopilot_current_shot ? " ? "+esc(run.autopilot_current_shot) : "";
    const progressText=plannedCount?'Shot '+Math.min(index||1,count)+'/'+count:'Codex is choosing the shot count';
    return '<section class="autopilot-box"><div class="autopilot-head"><strong>ONE-PROMPT AUTO-PILOT</strong><span>'+esc(labels[stage]||stage)+shot+'</span></div><div class="progress-track"><div class="progress-fill" style="width:'+percent+'%"></div></div><small>'+progressText+' - '+percent+'%</small></section>';
  }

  function renderRun(run, quiet=false) {
    const view=$("run-view"); const p=run.analysis; const hasPlan=!!p;
    $("page-title").textContent=p?.project_title||run.brief.title_hint||"Đang tạo dự án";
    updateStepper(run.status, Boolean(run.youtube_metadata_summary));
    const header=`<div class="section-head"><div><div class="eyebrow">RUN ${esc(run.run_id)}</div><h2>${esc(p?.project_title||"Codex đang chuẩn bị")}</h2><p>${esc(p?.episode?.title||"Brief đang được phân tích")}${run.project_dir?` · <span class="code">${esc(run.project_dir.replaceAll('\\','/').split('/').slice(-2).join('/'))}</span>`:""}</p></div><span class="status-tag ${badgeClass(run.status)}">${esc(statusLabel(run.status))}</span></div>`;
    let body="";
    if(run.status==="ANALYZING") body=`<div class="empty-state"><span class="spinner"></span><strong>Codex đang đọc brief và dựng phương án</strong><span>Ứng dụng chỉ nhận JSON theo schema; chưa gửi yêu cầu tới Muse.</span></div>`;
    if(run.status==="DRAFT_READY") body=`${planHtml(run)}<div class="notice">Khi duyệt, toàn bộ dự án vẫn được lưu trên đĩa. Bạn duyệt storyboard trước; manifest và usage được duyệt ở bước riêng.</div><div class="panel-actions"><button class="primary-button" id="approve-plan">Duyệt storyboard và tạo prompt shot đầu</button></div>`;
    if(run.status==="PLAN_APPROVED") body=`<div class="success-box">Storyboard đã được duyệt. Codex đã tạo prompt cho shot đầu; các shot phụ thuộc được giữ lại đến khi clip trước được review.</div>${shotSelector(run)}${run.selected_shot_id?`<div class="summary-box"><h3>PROMPT ĐÃ CHUẨN BỊ · ${esc(run.selected_shot_id)}</h3><pre class="prompt-preview">${esc(p?.episode?.shots?.find(s=>s.shot_id===run.selected_shot_id)?.prompt||"")}</pre></div>`:""}<div class="panel-actions"><button class="primary-button" id="make-manifest">Tạo manifest một shot</button></div>`;
    if(run.status==="REVIEWED" && run.next_shot_prompt) body=`${mediaHtml(run)}<div class="success-box">Continuity đã được ghi vào ledger. Codex đã tạo prompt shot kế tiếp từ actual end state và last frame đã review.</div>${shotSelector(run)}<pre class="prompt-preview">${esc(run.next_shot_prompt)}</pre><div class="panel-actions"><button class="primary-button" id="make-manifest">Lập manifest cho shot tiếp</button></div>`;
    if(run.status==="REVIEWED" && !run.next_shot_prompt) body=`${mediaHtml(run)}<div class="success-box">Đã review shot cuối. Có thể xuất episode khi mọi shot đều có trạng thái QC_PASSED.</div><div class="panel-actions"><button class="primary-button" id="export-episode">Render và QC episode</button></div>`;
    if(run.status==="MANIFEST_DRAFT") body=`${shotSelector(run)}${manifestHtml(run)}`;
    if(run.status==="MANIFEST_APPROVED") body=`${manifestHtml(run)}<div class="notice">Để gửi, nhập đúng cụm <b class="code">SEND ${esc(run.manifest_summary?.manifest_id)}</b>. Hành động này gửi đúng một request thật tới Muse.</div><label class="field"><span>Xác nhận gửi</span><input id="submit-confirmation" placeholder="SEND ${esc(run.manifest_summary?.manifest_id)}"></label><div class="panel-actions"><button class="danger-button" id="submit-generation">Gửi 1 request tới Muse</button></div>`;
    if(["SUBMITTED","RUNNING","POLL_ERROR"].includes(run.status)) body=`<div class="summary-box"><h3>TASK ID</h3><p class="code">${esc(run.task_id)}</p></div><div class="empty-state"><span class="spinner"></span><strong>${esc(statusLabel(run.status))}</strong><span>Ứng dụng chỉ poll task; không gửi lại yêu cầu.</span></div><div class="panel-actions"><button class="secondary-button" id="refresh-task">Kiểm tra trạng thái</button></div>`;
    if(["MEDIA_READY","QC_WARN","REVIEW_READY"].includes(run.status)) {
      body=`${mediaHtml(run)}${run.status==="REVIEW_READY"?reviewHtml(run):`<div class="notice">Clip đã được tải, kiểm tra stream, giải mã, trích frame và QC. Bấm nút dưới để gửi ba frame mẫu cho Codex phân tích continuity; ledger chỉ thay đổi sau khi bạn xác nhận kết quả.</div><div class="panel-actions"><button class="primary-button" id="analyze-continuity">Gửi 3 frame cho Codex review</button></div>`}`;
    }
    if(run.status==="EXPORTED" || run.status==="EXPORT_QC_WARN") {
      const metadata=run.youtube_metadata_summary;
      const metadataPanel=run.status==="EXPORTED"?`<section class="summary-box"><h3>YOUTUBE SEO & METADATA · BẢN NHÁP</h3>${metadata?`<p><b>Tiêu đề được chọn:</b> ${esc(metadata.selected_title)}</p><p><b>Thư mục:</b> <span class="code">${esc(metadata.directory)}</span></p><div><b>Top 3 title theo lint cấu trúc:</b>${(metadata.top_titles||[]).map((item,index)=>`<p>${index+1}. ${esc(item.title)} · ${esc(item.score)}/100 · ${esc((item.issues||[]).join("; ")||"không có cảnh báo")}</p>`).join("")}</div><p>${esc(metadata.chapter_count||0)} chapter · thumbnail lint: ${esc(metadata.thumbnail_helper_warning_count||0)} cảnh báo</p><pre>${esc(metadata.description||"")}</pre><p><b>Tags:</b> ${esc((metadata.tags||[]).join(", ")||"(không có)")}</p><p><b>Hashtags:</b> ${esc((metadata.hashtags||[]).join(" ")||"(không có)")}</p><p><b>Thumbnail concepts:</b> ${esc((metadata.thumbnail_concepts||[]).map(item=>`${item.recommendation}: ${item.focal_idea} · ${item.framing} · ${item.overlay_text||"không chữ"}`).join(" | "))}</p><p><b>Chapters:</b> ${esc((metadata.chapters||[]).map(item=>`${item.timestamp} ${item.title}`).join(" · ")||metadata.chapters_note||"Không có")}</p><div class="notice">Điểm lint là heuristic cấu trúc, không phải dự đoán hiệu quả. Không có nội dung nào được upload hoặc publish.</div>`:`<p>Codex sẽ nhận frame đầu/giữa/cuối của MP4, storyboard, continuity ledger và transcript nếu bạn cung cấp qua backend Codex/LLM đã cấu hình. Không gửi toàn bộ video hoặc audio. Bản nháp chỉ được lưu trên máy này.</p><label class="field full"><span>Transcript có timestamp (tùy chọn; cần để tạo chapter)</span><textarea id="youtube-transcript" maxlength="100000" placeholder="Dán nội dung SRT/VTT đã khớp với bản xuất. Bỏ trống nếu chưa có transcript; khi đó chapter sẽ được bỏ qua."></textarea><small>Codex chỉ tạo chapter khi transcript và thời lượng video đáp ứng điều kiện; bạn cần đối chiếu timestamp với MP4.</small></label><div class="panel-actions"><button class="primary-button" id="draft-youtube-metadata">Tạo bản nháp YouTube SEO & thumbnail</button></div>`}</section>`:"";
      body=`<div class="media-box"><video controls preload="metadata" src="/api/runs/${encodeURIComponent(run.run_id)}/video/export"></video></div><div class="success-box">Episode đã render: ${esc(run.export_path)} · QC ${esc(run.qc_report?.status)}</div>${metadataPanel}`;
    }
    if(run.status==="FAILED") body=`${hasPlan?planHtml(run):""}<div class="alert">${esc(run.error||"Codex hoặc provider báo lỗi.")}</div><div class="notice">Generation lỗi sẽ không tự gửi lại. Kiểm tra manifest, task record và gateway trước khi bắt đầu một request mới.</div>`;
    view.innerHTML=header+autopilotHtml(run)+(run.error&&run.status!=="FAILED"?`<div class="alert">${esc(run.error)}</div>`:"")+body;
    if(run.status==="DRAFT_READY") $("approve-plan")?.addEventListener("click",()=>action("/api/runs/"+run.run_id+"/approve-plan","POST",{confirm:true},"Đã duyệt storyboard"));
    if(["PLAN_APPROVED","REVIEWED"].includes(run.status) && run.next_shot_prompt!==null || run.status==="PLAN_APPROVED") {
      $("make-manifest")?.addEventListener("click",()=>action("/api/runs/"+run.run_id+"/manifest","POST",{shot_id:$("shot-select")?.value||run.selected_shot_id},"Đã tạo manifest DRAFT"));
    }
    $("approve-budget")?.addEventListener("click",()=>action("/api/runs/"+run.run_id+"/approve-generation","POST",{usage_estimate:$("usage-estimate").value,budget_limit:$("budget-limit").value,approved_by:$("approved-by").value},"Đã duyệt giới hạn cho manifest"));
    $("submit-generation")?.addEventListener("click",()=>action("/api/runs/"+run.run_id+"/submit","POST",{confirmation:$("submit-confirmation").value},"Đã gửi request một shot"));
    $("refresh-task")?.addEventListener("click",()=>action("/api/runs/"+run.run_id+"/refresh","POST",{},"Đã kiểm tra task"));
    $("analyze-continuity")?.addEventListener("click",()=>action("/api/runs/"+run.run_id+"/continuity-review","POST",{},"Codex đã phân tích frame"));
    $("accept-review")?.addEventListener("click",()=>action("/api/runs/"+run.run_id+"/accept-review","POST",{confirm:true},"Đã ghi continuity và chuẩn bị shot tiếp"));
    $("export-episode")?.addEventListener("click",()=>action("/api/runs/"+run.run_id+"/export","POST",{},"Đã render episode"));
    $("draft-youtube-metadata")?.addEventListener("click",async()=>{const button=$("draft-youtube-metadata");button.disabled=true;try{await action("/api/runs/"+run.run_id+"/youtube-metadata","POST",{timestamped_transcript:$("youtube-transcript")?.value||""},"Đã lưu bản nháp YouTube metadata");}finally{button.disabled=false;}});
  }

  function reviewHtml(run) {
    const review=run.continuity_assessment||{};
    const state=review.actual_end_state||{};
    return `<div class="review-grid"><div class="review-box"><h3>ACTUAL END STATE · CODEx ĐỀ XUẤT</h3><pre>${esc(JSON.stringify(state,null,2))}</pre></div><div class="review-box"><h3>GHI CHÚ REVIEW</h3><pre>${esc((review.reviewer_notes||[]).join("\n\n")||"Không có")}</pre></div><div class="review-box"><h3>CONTINUITY RISKS</h3><pre>${esc((review.continuity_risks||[]).join("\n\n")||"Không có")}</pre></div></div><div class="notice">Hãy xem video và frame ở trên. Chỉ xác nhận nếu observation phản ánh clip thực tế; xác nhận sẽ cập nhật continuity ledger và tạo prompt cho shot tiếp theo.</div><div class="panel-actions"><button class="primary-button" id="accept-review">Xác nhận review và tạo prompt shot kế</button></div>`;
  }

  async function refreshRun(quiet=false) {
    if(!activeRunId) return;
    try { const run=await api(`/api/runs/${encodeURIComponent(activeRunId)}`);renderRun(run,quiet);await loadRuns();if(["EXPORTED","EXPORT_QC_WARN","FAILED"].includes(run.status)&&timer){clearInterval(timer);timer=null;} }
    catch(error) { if(!quiet) toast(error.message,true); }
  }

  async function action(path,method,body,message) {
    try { await api(path,method,body);toast(message);await refreshRun(); }
    catch(error) { toast(error.message,true);await refreshRun(true); }
  }

  $("brief-form").addEventListener("submit",async(event)=>{
    event.preventDefault();
    const form=new FormData(event.currentTarget);
    const payload=Object.fromEntries(form.entries());
    payload.episode_duration_seconds=Number(payload.episode_duration_seconds);
    const button=$("analyze-button");button.disabled=true;button.innerHTML='<span class="spinner"></span> Đang tạo bản nháp…';
    try {
      const run=await api("/api/runs","POST",payload);activeRunId=run.run_id;
      $("new-view").classList.add("hidden");$("run-view").classList.remove("hidden");
      renderRun(run);await loadRuns();
      if(timer)clearInterval(timer);timer=setInterval(()=>refreshRun(true),2500);
    } catch(error) { toast(error.message,true); }
    finally { button.disabled=false;button.textContent="Tạo bản nháp"; }
  });

  $("new-run").addEventListener("click",()=>{
    activeRunId=null;if(timer)clearInterval(timer);$("page-title").textContent="Bắt đầu một câu chuyện";$("run-view").classList.add("hidden");$("new-view").classList.remove("hidden");updateStepper("NEW");
  });

  loadHealth();loadRuns();setInterval(loadHealth,15000);
})();
