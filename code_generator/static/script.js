document.addEventListener('DOMContentLoaded', () => {
    // Resizer Logic
    const resizer = document.getElementById('drag-me');
    const leftSide = document.querySelector('.input-section');
    const rightSide = document.querySelector('.output-section');

    // Set initial panel sizes: left 40%, right 60%
    if (leftSide && rightSide) {
        leftSide.style.flex = '0 0 calc(40% - 0.5rem)';
        rightSide.style.flex = '0 0 calc(60% - 0.5rem)';
    }

    let isResizing = false;

    if (resizer) {
        resizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            document.body.classList.add('is-resizing');
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;

            const container = leftSide.parentElement;
            const containerRect = container.getBoundingClientRect();

            // Calculate new width percent for left side based on mouse pos
            let newLeftWidth = e.clientX - containerRect.left;

            // Minimum widths (e.g., 200px)
            if (newLeftWidth < 200) newLeftWidth = 200;
            if (newLeftWidth > containerRect.width - 200) newLeftWidth = containerRect.width - 200;

            const leftPercent = (newLeftWidth / containerRect.width) * 100;
            const rightPercent = 100 - leftPercent;

            leftSide.style.flex = `0 0 calc(${leftPercent}% - 0.5rem)`;
            rightSide.style.flex = `0 0 calc(${rightPercent}% - 0.5rem)`;

            // Resize canvas if active
            if (document.getElementById('draw-tab').classList.contains('active')) {
                resizeFabricCanvas();
            }
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                document.body.classList.remove('is-resizing');
            }
        });
    }

    // Canvas Resizers
    const canvasWrapper = document.getElementById('canvas-wrapper');
    const widthResizer = document.getElementById('canvas-width-resizer');
    const heightResizer = document.getElementById('canvas-height-resizer');

    let isResizingCanvas = false;
    let resizeType = '';

    if (widthResizer) {
        widthResizer.addEventListener('mousedown', (e) => {
            isResizingCanvas = true;
            resizeType = 'width';
            document.body.classList.add('is-resizing');
            e.preventDefault();
        });
    }

    if (heightResizer) {
        heightResizer.addEventListener('mousedown', (e) => {
            isResizingCanvas = true;
            resizeType = 'height';
            document.body.classList.add('is-resizing');
            e.preventDefault();
        });
    }

    document.addEventListener('mousemove', (e) => {
        if (!isResizingCanvas || !canvasWrapper) return;

        if (resizeType === 'width') {
            const wrapperRect = canvasWrapper.getBoundingClientRect();
            let newWidth = e.clientX - wrapperRect.left;
            if (newWidth < 200) newWidth = 200;
            if (newWidth > 800) newWidth = 800;
            canvasWrapper.style.width = newWidth + 'px';
        } else if (resizeType === 'height') {
            const wrapperRect = canvasWrapper.getBoundingClientRect();
            let newHeight = e.clientY - wrapperRect.top;
            if (newHeight < 200) newHeight = 200;
            if (newHeight > 600) newHeight = 600;
            canvasWrapper.style.height = newHeight + 'px';
        }
    });

    document.addEventListener('mouseup', () => {
        if (isResizingCanvas) {
            isResizingCanvas = false;
            resizeType = '';
            document.body.classList.remove('is-resizing');
            resizeFabricCanvas();
        }
    });

    // Tab switching logics
    const inputTabs = document.querySelectorAll('.tab-btn');
    const inputContents = document.querySelectorAll('.tab-content');

    inputTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            inputTabs.forEach(t => t.classList.remove('active'));
            inputContents.forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            document.getElementById(tab.dataset.tab).classList.add('active');

            // Resize canvas if switching to draw tab
            if (tab.dataset.tab === 'draw-tab') {
                setTimeout(resizeFabricCanvas, 10);
                // Reduce left panel size when draw tab is active
                leftSide.style.flex = '0 0 250px';
                rightSide.style.flex = '1';
            }
        });
    });

    const outputTabs = document.querySelectorAll('.out-tab-btn');
    const outputContents = document.querySelectorAll('.out-tab-content');

    outputTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            outputTabs.forEach(t => t.classList.remove('active'));
            outputContents.forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            document.getElementById(tab.dataset.tab).classList.add('active');
        });
    });

    // Upload logic
    const dropZoneElement = document.getElementById("drop-zone");
    const inputElement = document.getElementById("file-input");
    const imagePreview = document.getElementById("image-preview");
    const clearUploadBtn = document.getElementById("clear-upload-btn");
    let currentFile = null;

    dropZoneElement.addEventListener("click", () => {
        inputElement.click();
    });

    inputElement.addEventListener("change", (e) => {
        if (inputElement.files.length) {
            updateThumbnail(inputElement.files[0]);
        }
    });

    dropZoneElement.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZoneElement.classList.add("over");
    });

    ["dragleave", "dragend"].forEach((type) => {
        dropZoneElement.addEventListener(type, () => {
            dropZoneElement.classList.remove("over");
        });
    });

    dropZoneElement.addEventListener("drop", (e) => {
        e.preventDefault();
        if (e.dataTransfer.files.length) {
            inputElement.files = e.dataTransfer.files;
            updateThumbnail(e.dataTransfer.files[0]);
        }
        dropZoneElement.classList.remove("over");
    });

    function updateThumbnail(file) {
        if (file.type.startsWith("image/")) {
            currentFile = file;
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => {
                imagePreview.src = reader.result;
                imagePreview.classList.remove("hidden");
                dropZoneElement.classList.add("hidden");
                clearUploadBtn.classList.remove("hidden");
            };
        }
    }

    clearUploadBtn.addEventListener("click", () => {
        currentFile = null;
        inputElement.value = "";
        imagePreview.src = "";
        imagePreview.classList.add("hidden");
        dropZoneElement.classList.remove("hidden");
        clearUploadBtn.classList.add("hidden");
    });

    // Advanced Drawing Canvas Logic (Fabric.js)
    let fabricCanvas = new fabric.Canvas('drawing-canvas', {
        isDrawingMode: true,
        backgroundColor: '#ffffff',
        width: 2000,
        height: 2000
    });

    fabricCanvas.freeDrawingBrush.color = '#000000';
    fabricCanvas.freeDrawingBrush.width = 3;

    // Undo/Redo Logic
    let isHistoryAction = false;
    let history = [];
    let historyIndex = -1;

    function saveHistory() {
        if (isHistoryAction) return;
        const json = JSON.stringify(fabricCanvas);
        history = history.slice(0, historyIndex + 1);
        history.push(json);
        historyIndex++;
    }

    fabricCanvas.on('object:added', saveHistory);
    fabricCanvas.on('object:modified', saveHistory);
    fabricCanvas.on('object:removed', saveHistory);

    // Initial state
    setTimeout(saveHistory, 200);

    const undoBtn = document.getElementById('undo-btn');
    if (undoBtn) {
        undoBtn.addEventListener('click', () => {
            if (historyIndex > 0) {
                isHistoryAction = true;
                historyIndex--;
                fabricCanvas.loadFromJSON(history[historyIndex], () => {
                    fabricCanvas.renderAll();
                    isHistoryAction = false;
                });
            }
        });
    }

    const redoBtn = document.getElementById('redo-btn');
    if (redoBtn) {
        redoBtn.addEventListener('click', () => {
            if (historyIndex < history.length - 1) {
                isHistoryAction = true;
                historyIndex++;
                fabricCanvas.loadFromJSON(history[historyIndex], () => {
                    fabricCanvas.renderAll();
                    isHistoryAction = false;
                });
            }
        });
    }

    function resizeFabricCanvas() {
        const wrapper = document.getElementById('canvas-wrapper');
        if (wrapper && wrapper.clientWidth > 0) {
            fabricCanvas.setWidth(wrapper.clientWidth);
            fabricCanvas.setHeight(wrapper.clientHeight);
            fabricCanvas.renderAll();
        }
    }

    setTimeout(resizeFabricCanvas, 100);
    window.addEventListener('resize', resizeFabricCanvas);

    // Toolbar logic
    const toolBtns = document.querySelectorAll('.tool-btn');

    function setActiveTool(btnId) {
        toolBtns.forEach(btn => btn.classList.remove('active'));
        document.getElementById(btnId).classList.add('active');
    }

    document.getElementById('draw-mode-btn').addEventListener('click', () => {
        fabricCanvas.isDrawingMode = true;
        setActiveTool('draw-mode-btn');
    });

    document.getElementById('select-mode-btn').addEventListener('click', () => {
        fabricCanvas.isDrawingMode = false;
        setActiveTool('select-mode-btn');
    });

    document.getElementById('add-rect-btn').addEventListener('click', () => {
        fabricCanvas.isDrawingMode = false;
        setActiveTool('select-mode-btn');
        const rect = new fabric.Rect({
            left: 50, top: 50, fill: 'transparent',
            stroke: document.getElementById('drawing-color').value,
            strokeWidth: parseInt(document.getElementById('drawing-width').value),
            width: 100, height: 50
        });
        fabricCanvas.add(rect);
    });

    document.getElementById('add-circle-btn').addEventListener('click', () => {
        fabricCanvas.isDrawingMode = false;
        setActiveTool('select-mode-btn');
        const circle = new fabric.Circle({
            left: 50, top: 50, fill: 'transparent',
            stroke: document.getElementById('drawing-color').value,
            strokeWidth: parseInt(document.getElementById('drawing-width').value),
            radius: 30
        });
        fabricCanvas.add(circle);
    });

    document.getElementById('add-text-btn').addEventListener('click', () => {
        fabricCanvas.isDrawingMode = false;
        setActiveTool('select-mode-btn');
        const text = new fabric.IText('Double click to edit', {
            left: 50, top: 50, fontFamily: 'Inter',
            fill: document.getElementById('drawing-color').value, fontSize: 20
        });
        fabricCanvas.add(text);
    });

    document.getElementById('add-button-btn').addEventListener('click', () => {
        fabricCanvas.isDrawingMode = false;
        setActiveTool('select-mode-btn');

        const text = new fabric.IText(' Button ', {
            left: 50, top: 50, fontFamily: 'Inter',
            fill: '#ffffff', backgroundColor: document.getElementById('drawing-color').value,
            fontSize: 20
        });

        fabricCanvas.add(text);
        fabricCanvas.setActiveObject(text);
    });

    document.getElementById('drawing-color').addEventListener('input', (e) => {
        fabricCanvas.freeDrawingBrush.color = e.target.value;
        const activeObj = fabricCanvas.getActiveObject();
        if (activeObj) {
            if (activeObj.type === 'i-text' || activeObj.type === 'text') {
                activeObj.set('fill', e.target.value);
            } else if (activeObj.type === 'group') {
                activeObj.item(0).set('fill', e.target.value);
            } else {
                activeObj.set('stroke', e.target.value);
            }
            fabricCanvas.renderAll();
        }
    });

    document.getElementById('drawing-width').addEventListener('input', (e) => {
        fabricCanvas.freeDrawingBrush.width = parseInt(e.target.value, 10);
        const activeObj = fabricCanvas.getActiveObject();
        if (activeObj && activeObj.type !== 'i-text' && activeObj.type !== 'group') {
            activeObj.set('strokeWidth', parseInt(e.target.value, 10));
            fabricCanvas.renderAll();
        }
    });

    document.getElementById('delete-item-btn').addEventListener('click', () => {
        const activeObjects = fabricCanvas.getActiveObjects();
        if (activeObjects.length) {
            activeObjects.forEach(function (object) {
                fabricCanvas.remove(object);
            });
            fabricCanvas.discardActiveObject();
        }
    });

    // Keyboard shortcuts for delete
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Delete' || e.key === 'Backspace') {
            const activeObj = fabricCanvas.getActiveObject();
            if (activeObj && !activeObj.isEditing) {
                const activeObjects = fabricCanvas.getActiveObjects();
                if (activeObjects.length) {
                    activeObjects.forEach(obj => fabricCanvas.remove(obj));
                    fabricCanvas.discardActiveObject();
                }
            }
        }
    });

    document.getElementById('clear-canvas-btn').addEventListener('click', () => {
        fabricCanvas.clear();
        fabricCanvas.backgroundColor = '#ffffff';
        fabricCanvas.renderAll();
    });

    // Generate Code Logic
    const generateBtn = document.getElementById('generate-btn');
    const codeOutput = document.getElementById('code-output');
    const livePreview = document.getElementById('live-preview');
    const loadingDiv = document.getElementById('loading');

    // Step management functions
    function initializeSteps() {
        const steps = ['preprocessing', 'detection', 'analysis', 'generation', 'complete'];
        steps.forEach(step => {
            const stepElement = document.getElementById(`step-${step}`);
            if (stepElement) {
                stepElement.classList.remove('active', 'completed');
            }
        });
    }

    function completeStep(stepName) {
        const stepElement = document.getElementById(`step-${stepName}`);
        if (stepElement) {
            stepElement.classList.remove('active');
            stepElement.classList.add('completed');
            // Move to next step immediately after completion
            const steps = ['preprocessing', 'detection', 'analysis', 'generation', 'complete'];
            const currentIndex = steps.indexOf(stepName);
            if (currentIndex < steps.length - 1) {
                activateStep(steps[currentIndex + 1]);
            }
        }
    }

    function activateStep(stepName) {
        const stepElement = document.getElementById(`step-${stepName}`);
        if (stepElement) {
            stepElement.classList.add('active');
            stepElement.classList.remove('completed');
        }
    }

    generateBtn.addEventListener('click', async () => {
        const activeTab = document.querySelector('.tab-btn.active').dataset.tab;
        const framework = document.getElementById('framework-select').value;
        let blobToUpload = null;

        if (activeTab === 'upload-tab') {
            if (!currentFile) {
                alert("Please upload an image first.");
                return;
            }
            blobToUpload = currentFile;
        } else {
            // Get from canvas
            // Temporary set scaling back to 1 if it has retina to avoid huge images for Gemini
            const dataUrl = fabricCanvas.toDataURL('image/png');
            blobToUpload = await (await fetch(dataUrl)).blob();
        }

        const formData = new FormData();
        formData.append('image', blobToUpload, 'sketch.png');
        formData.append('framework', framework);

        loadingDiv.classList.remove('hidden');
        generateBtn.disabled = true;

        // Initialize and start steps
        initializeSteps();
        activateStep('preprocessing');

        try {
            // Mark preprocessing as starting
            activateStep('preprocessing');
            
            // Simulate quick preprocessing completion (actual happens server-side)
            setTimeout(() => completeStep('preprocessing'), 500);
            
            // After preprocessing, text extraction starts
            setTimeout(() => {
                if (!document.getElementById('step-detection').classList.contains('completed')) {
                    activateStep('detection');
                }
            }, 600);
            
            // After text extraction detection starts
            setTimeout(() => {
                if (!document.getElementById('step-analysis').classList.contains('completed')) {
                    activateStep('analysis');
                }
            }, 1200);
            
            // Then activate code generation when API call happens
            setTimeout(() => {
                if (!document.getElementById('step-generation').classList.contains('completed')) {
                    activateStep('generation');
                }
            }, 1800);
            
            const response = await fetch('/api/generate', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Server error");
            }

            const data = await response.json();
            const mdCode = data.code;

            // Mark generation step as complete when response arrives
            completeStep('generation');

            // Extract code from markdown wrapper if exists
            let cleanCode = mdCode;
            const mdMatch = mdCode.match(/```[a-zA-Z]*\n([\s\S]*?)\n```/);
            if (mdMatch && mdMatch[1]) {
                cleanCode = mdMatch[1];
            }

            codeOutput.value = cleanCode;

            // Switch to code tab automatically
            document.querySelector('.out-tab-btn[data-tab="code-view-tab"]').click();

            // Setup preview if HTML or React+Tailwind CDN
            if (framework.includes('HTML') || framework.includes('React with Tailwind')) {
                let htmlContent = cleanCode;
                if (!htmlContent.includes('<html')) {
                    htmlContent = `<!DOCTYPE html><html><head><script src="https://cdn.tailwindcss.com"></script></head><body>${cleanCode}</body></html>`;
                }
                livePreview.srcdoc = htmlContent;
            } else {
                livePreview.srcdoc = `<!DOCTYPE html><html><body><h3 style="font-family:sans-serif; text-align:center; margin-top:50px; color:#555;">Live preview not directly available for ${framework} in this sandbox. Please copy the code and run it in your environment.</h3></body></html>`;
            }

        } catch (error) {
            alert(`Error generating code: ${error.message}`);
        } finally {
            // Hide loading after a short delay to show completion
            setTimeout(() => {
                loadingDiv.classList.add('hidden');
                generateBtn.disabled = false;
            }, 1500);
        }
    });

    // Copy block
    document.getElementById('copy-btn').addEventListener('click', () => {
        codeOutput.select();
        document.execCommand('copy');

        const btn = document.getElementById('copy-btn');
        const originalText = btn.innerText;
        btn.innerText = 'Copied!';
        setTimeout(() => {
            btn.innerText = originalText;
        }, 2000);
    });
});
