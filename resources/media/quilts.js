
var LINE_SPACING = 10;
var MARGIN = 2;
var F_HEIGHT = 10;       // height of the row with "F" (families)

/**
 * Decorates a <canvas> element to show a quilts layout.
 *
 * @param {jQuery} canvas   The element to decorate.
 * @param {Array.<*>} families
 *    The data from the server. It has the following format:
 *        families ::= [ families_in_layer+ ]
 *        families_in_layer ::= [ family+ ]
 *        family ::= [father || -1, mother || -1, child1, child2,...]
 */

function QuiltsCanvas(canvas, layers, families) {
    this.scale = 1.0;
    this.left = 0.0;
    this.top = 0.0;

    this.layers = layers;  // list of people in each layer
    this.families = families;

    this.canvas = canvas[0];
    this.canvas.width = canvas.width();
    this.canvas.height = canvas.height();

    canvas
        .wheel($.proxy(this.on_wheel_, this))
        .start_drag($.proxy(this.on_start_drag_, this))
        .in_drag($.proxy(this.on_in_drag_, this))

    // Preprocess the data to gather information relative to each person in a
    // datastructure easier to manipulate

    this.personToLayer = {};   //  id of person -> [layer, index in layer]
    for (var layer = 0; layer < layers.length; layer++) {
        for (var person = 0; person < layers[layer].length; person++) {
            var p = layers[layer][person];
            var sex = p[2];
            p.name =
                (sex == "F" ? '\u2640' : sex == "M" ? '\u2642' : ' ') + p[1];

            var id = p[0];
            this.personToLayer[id] = {
                layer: layer,
                index: person,  // index in layer
                sex: sex /* sex */,
                rightMostMarriageLayer: layers.length,
                rightMostMarriageIndex: 0};
        }
    }

    // Analyze data from the families, needed for further display.

    for (var layer = 0; layer < families.length; layer++) {
        var families_in_layer = families[layer];
        for (var family = 0; family < families_in_layer.length; family++) {
            var fam = families_in_layer[family];
            for (var person = 0; person < fam.length; person++) {
                var p = fam[person];
                if (p != -1) {
                    p = this.personToLayer[p];
                    if (p.rightMostMarriageLayer > layer) {
                        p.rightMostMarriageLayer = layer;
                        p.rightMostMarriageIndex = family;
                    }
                }
            }
        }
    }

    // Compute the size and position of each layers. These do not change when
    // the canvas is scrolled or zoomed, so they can be precomputed (especially
    // because computing the size of text is relatively expensive). This also
    // allows us to only draw the visible layers later on.

    var ctx = this.canvas.getContext("2d");

    this.lefts = [];          // left corner for each layer
    this.rights = [];         // right corner for each layer
    this.tops = [];           // top corner for each layer
    this.heights = [];        // heights of each layer

    var layerX = 10;         // top-left corner of current layer
    var layerY = 10;         // top-left corner of current layer
    var prevLayer;           // index of previous non-empty layer

    for (var layer = this.layers.length - 1; layer >= 0; layer--) {
        if (this.layers[layer].length) {
            var y = layerY + LINE_SPACING;
            var maxWidth = 0;

            for (var persona = 0; persona < this.layers[layer].length; persona++) {
                var name = this.layers[layer][persona].name;
                maxWidth = Math.max(maxWidth, ctx.measureText(name).width);
                y += LINE_SPACING;
            }

            var width = maxWidth + 2 * MARGIN;
            var height = y - layerY - LINE_SPACING;

            this.tops[layer] = layerY;
            this.lefts[layer] = layerX;
            this.rights[layer] = layerX + width;
            this.heights[layer] = height;

            layerX = this.rights[layer] +
                this.families[layer].length * LINE_SPACING;

            if (this.families[layer].length) {
                layerY += height + F_HEIGHT;
            } else {
                layerY += height;
            }
        }
    }
};

/**
 * Convert an X coordinate from pixels to absolute
 * @param {number} xpixel  pixel coordinate.
 * @return {number}        absolute coordinate.
 */

QuiltsCanvas.prototype.toAbsX = function(xpixel) {
    return xpixel / this.scale + this.left;
};

/**
 * Convert a Y coordinate from pixels to absolute
 * @param {number} ypixel  pixel coordinate.
 * @return {number}        absolute coordinate.
 */

QuiltsCanvas.prototype.toAbsY = function(ypixel) {
    return ypixel / this.scale + this.top;
};

/**
 * Convert an X coordinate from absolute to pixels
 * @param {number} xabs    absolute coordinate.
 * @return {number}        pixel coordinate.
 */

QuiltsCanvas.prototype.toPixelX = function(xabs) {
    return (xabs - this.left) * this.scale;
};

/**
 * Convert a Y coordinate from absolute to pixels
 * @param {number} yabs    absolute coordinate.
 * @return {number}        pixel coordinate.
 */

QuiltsCanvas.prototype.toPixelY = function(yabs) {
    return (yabs - this.top) * this.scale;
};

/**
 * Update the scale of the canvas, keeping (xoffs, yoffs) in place.
 */

QuiltsCanvas.prototype.updateZoom = function(newScale, xoffs, yoffs) {
    var old_scale = this.scale;
    var offset = $(this.canvas).offset();
    var xabs = this.toAbsX(xoffs - offset.left);
    var yabs = this.toAbsY(yoffs - offset.top);

    this.scale = newScale;

    // Keep the mouse position constant on the screen (ie do not move the
    // pixel we are pointing to).
    // if mx is screen coordinate of mouse, this must remain constant.
    //   mx = (mxabs - oldx) * oldz
    //      = (mxabs - this.x) * this.scale
    //   => this.x = mxabs - (mxabs - oldx) * oldz / this.scale

    this.left = xabs - (xabs - this.left) * old_scale / this.scale;
    this.top = yabs - (yabs - this.top) * old_scale / this.scale;
    this.draw();
};

/**
 * Mouse Wheel events
 */

QuiltsCanvas.prototype.on_wheel_ = function(e) {
    if (e.delta > 0) {
        this.updateZoom(this.scale * 1.1, e.clientX, e.clientY);
    } else {
        this.updateZoom(this.scale / 1.1, e.clientX, e.clientY);
    }
    return false;
};

/**
 * Handles the beginning of a scroll operation (via drag).
 */

QuiltsCanvas.prototype.on_start_drag_ = function(e, dragdata) {
    dragdata.offset = {left: this.left,
                       top: this.top};
    dragdata.scale = 1 / -this.scale;
};

/**
 * Handles a scroll of the canvas via mouse drag.
 */

QuiltsCanvas.prototype.on_in_drag_ = function(e, dragdata) {
    this.left = dragdata.offset.left;
    this.top = dragdata.offset.top;
    this.draw();
};

/**
 * Draw either a square or circle in a matrix, depending on the sex of the
 * person.
 */

QuiltsCanvas.prototype.drawPersonSymbol_ = function(ctx, sex, left, top) {
    ctx.beginPath();
    if (sex == "F") {
        ctx.arc(left + LINE_SPACING / 2,
                top + LINE_SPACING / 2,
                LINE_SPACING / 2, 0, 2 * Math.PI);
    } else if (sex == "M") {
        ctx.fillRect(left, top, LINE_SPACING, LINE_SPACING);
    } else {
        ctx.fillRect(left + 4, top + 4, LINE_SPACING - 8, LINE_SPACING - 8);
    }
    ctx.fill();
};

/**
 * Display the box for a single layer
 */

QuiltsCanvas.prototype.displayLayer_ = function(ctx, layer) {
    ctx.beginPath();   
    var la = this.layers[layer];
    if (la.length) {
        var y = this.tops[layer] + LINE_SPACING - MARGIN;
        for (var p = 0; p < la.length; p++) {
            ctx.fillText(la[p].name, this.lefts[layer] + MARGIN, y);
            y += LINE_SPACING;
        }
        ctx.rect(this.lefts[layer], this.tops[layer], 
                 this.rights[layer] - this.lefts[layer], 
                 this.heights[layer]);
    }
    ctx.stroke();
};

/**
 * Display the marriages matrix.
 *
 * The horizontal line should extend in the current matrix at least to the
 * right-most vertical line that has at least this height. This will
 * display a diagonal matrix when possible.
 */

QuiltsCanvas.prototype.displayMarriages_ = function(ctx, layer) {
    var right = this.rights[layer + 1];
    var top = this.tops[layer + 1];
    var prevFamilies = this.families[layer + 1];
    var prevLayer = this.layers[layer + 1];

    ctx.save();
    ctx.translate(right, 0);

    var mins = [];   // for each vertical line, its minY
    var prevMinY = this.tops[layer];

    ctx.strokeStyle = "gray";
    ctx.fillStyle = "black";
    for (var m = 0; m < prevFamilies.length; m++) {
        var minY   = this.tops[layer];
        
        for (var p = 0; p < 2; p++) {
            var person = prevFamilies[m][p];
            if (person != -1) {
                var info = this.personToLayer[person];
                var y = this.tops[info.layer] + info.index * LINE_SPACING;
                minY = Math.min(minY, y);
                this.drawPersonSymbol_(
                    ctx, info.sex, m * LINE_SPACING, y);
            }
        }

        mins[m] = Math.min(prevMinY, minY);
        prevMinY = minY;

        ctx.beginPath();
        var x = m * LINE_SPACING;
        ctx.moveTo(x, mins[m]);
        ctx.lineTo(x, this.tops[layer]);
        ctx.stroke();
    }

    ctx.beginPath();
    var x = m * LINE_SPACING;
    mins[m] = minY;
    ctx.moveTo(x, minY);
    ctx.lineTo(x, this.tops[layer]);
    ctx.stroke();

    var prevMaxX = right;
    
    ctx.beginPath();
    for (var p1 = 0; p1 < prevLayer.length; p1++) {
        var id = prevLayer[p1][0];
        var info = this.personToLayer[id];
        var y = p1 * LINE_SPACING + top;
        var maxX = right;

        for (var m = mins.length - 1; m > 0; m--) {
            if (mins[m] <= y) {
                maxX = right + m * LINE_SPACING;
                break;
            }
        }

        if (info.rightMostMarriageLayer < this.layers.length) {
            maxX = Math.max(
                maxX,
                info.rightMostMarriageIndex * LINE_SPACING
                    + this.rights[info.rightMostMarriageLayer]);
        }

        if (maxX != right) {
            ctx.moveTo(0, y);
            ctx.lineTo(Math.max(maxX, prevMaxX) - right, y);
        }

        prevMaxX = maxX;
    }

    if (prevMaxX > this.lefts[layer]) {
        var y = p1 * LINE_SPACING + top;
        ctx.moveTo(0, y);
        ctx.lineTo(prevMaxX - right, y);
    }

    ctx.stroke();
    ctx.restore();
};

/**
 * Display the children matrix
 */

QuiltsCanvas.prototype.displayChildren_ = function(ctx, layer) {
    var right = this.rights[layer + 1];
    var prevFamilies = this.families[layer + 1];
    
    ctx.save();
    ctx.translate(right, this.tops[layer]);
    ctx.fillStyle = "black";
    ctx.strokeStyle = "gray";

    var maxs = [];  //  for each vertical line, its maximum Y
    var prevMaxY = 0;

    for (var m = 0; m < prevFamilies.length; m++) {
        var maxY = 0;
        for (var c = 2; c < prevFamilies[m].length; c++) {
            var child = prevFamilies[m][c];
            var info = this.personToLayer[child];
            var y = info.index * LINE_SPACING;
            maxY = Math.max(maxY, y);
            this.drawPersonSymbol_( ctx, info.sex, m * LINE_SPACING, y);
        }
        maxs[m] = Math.max(prevMaxY, maxY);
        prevMaxY = maxY;

        ctx.beginPath();
        var x = m * LINE_SPACING;
        ctx.moveTo(x, 0);
        ctx.lineTo(x, maxs[m]);
        ctx.stroke();
    }

    ctx.beginPath();
    for (var p1 = 1; p1 <= this.layers[layer].length; p1++) {
        var y = p1 * LINE_SPACING;
        var minX = this.lefts[layer] - right;

        for (var m = maxs.length - 1; m > 0; m--) {
            if (maxs[m] >= y) {
                minX = m * LINE_SPACING;
            }
        }

        ctx.moveTo(minX, y);
        ctx.lineTo(this.lefts[layer] - right, y);
    }
    ctx.stroke();
    ctx.restore();
};

/**
 * Redisplay the contents of the canvas.
 */

QuiltsCanvas.prototype.draw = function() {
    var ctx = this.canvas.getContext("2d");

    ctx.save();
    ctx.setTransform(
        1, 0, 0,
        1, 0, 0);
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.restore();

    ctx.fillStyle = "black";
    ctx.setTransform(
        this.scale, 0, 0,
        this.scale, -this.scale * this.left, -this.scale * this.top);

    for (var layer = this.layers.length - 1; layer >= 0; layer--) {
        // only display visible layers
        if (!(this.rights[layer] < this.left) ||
            !(this.lefts[layer] > this.left + this.canvas.width))
        {
            this.displayLayer_(ctx, layer);

            if (layer < this.layers.length - 1) {
                this.displayMarriages_(ctx, layer);
                
                // Display the row with "F" to separate couples and children
                
                ctx.save();
                ctx.beginPath();
                ctx.fillStyle = "#AAAAAA";
                ctx.rect(
                    this.rights[layer + 1] - 1, this.tops[layer] - F_HEIGHT,
                    this.lefts[layer] - this.rights[layer + 1], F_HEIGHT);
                ctx.fill();
                ctx.restore();
                
                this.displayChildren_(ctx, layer);
            }
        }
    }
};
