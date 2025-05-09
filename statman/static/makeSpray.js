function makeSpray(plays, name, num, fieldSVG, statPlayer, wait, career, bats){
    var colScale = d3.scaleLinear().domain([0,1]).range(['white', 'red'])

    var plays = plays.filter(function(d){ return d.OUTCOME != null & d.OUTCOME != 'null'})
    let buckets = []
    let hrBuckets = []
    var infPlays = plays.filter(function(d){ return ['3b', 'third base', 'ss', 'shortstop',
    'through the left side', 'up the middle', '2b', 'second base', 'through the right side',
    '1b', 'first base', 'p', 'c'].indexOf(d.LOCATION) > -1})

    var ofPlays = plays.filter(function(d){ return ['lf', 'left', 'lf line', 'left center',
    'cf', 'center', 'rf', 'right', 'rf line', 'right center'].indexOf(d.LOCATION) > -1})

    plays = infPlays.concat(ofPlays)

    // infPlaysEx = infPlays.filter(function(d){ return d.LOCATION != 'p' & d.LOCATION != 'c' }).length
    infPlaysEx = infPlays.length
    infPlays = infPlays.length
    ofPlays = ofPlays.length

    const locDict = {
      '1': ['3b', 'third base'],
      '2': ['ss', 'shortstop', 'through the left side'],
      '3': ['up the middle', 'p', 'c'],
      '4': ['2b', 'second base', 'through the right side'],
      '5': ['1b', 'first base'],
      '6': ['lf', 'left', 'lf line', 'left center'],
      '7': ['cf', 'center'],
      '8': ['rf', 'right', 'rf line', 'right center'],
    }

    const plotDict = {
      '0': [235,300],
      '1': [277,280],
      '2': [325,270],
      '3': [373,280],
      '4': [415,300],
      '5': [165, 170],
      '6': [325, 120],
      '7': [485, 170]
    }

    const hrDict = {
      '5': [125, 70],
      '6': [325, 20],
      '7': [525, 70]
    }

    const outcomes = ['1B', '2B', '3B', 'HR', 'LD','FB', 'GB']

    const stats = ['BA', 'OBP', 'SLG', 'K', 'BB', 'SB', 'CS']

    const outNameMap = {
      '1B': '1B',
      '2B': '2B',
      '3B': '3B',
      'HR': 'HR',
      'LD': 'LO',
      'FB': 'FO',
      'GB': 'GO'
    }

    for(loc in locDict){
      if(loc < 9){
        buckets.push({
         'loc': loc,
         'plays': plays.filter(function(d){return locDict[loc].indexOf(d.LOCATION.replace(';','')) > -1})
        })
        hrBuckets.push({
         'loc': loc,
         'plays': plays.filter(function(d){return locDict[loc].indexOf(d.LOCATION.replace(';','')) > -1 & d.OUTCOME == 'HR'})
        })
      }else{
        middle = plays.filter(function(d){return locDict[loc].indexOf(d.LOCATION.replace(';','')) > -1})
        for(i = 0; i < middle.length; ++i){
          ssRate = (buckets[1].plays.length+buckets[0].plays.length)/(infPlays)
          if(Math.random() < ssRate){
            buckets[1].plays.push(middle[i])
          }else{
            buckets[2].plays.push(middle[i])
          }
        }
      }
    }


    var margins = {'bottom': '5', 'left': '5', 'right': '5', 'top': '5'}
    var height = d3.select(fieldSVG).attr('height')
    var width = d3.select(fieldSVG).attr('width')
    var field = d3.select(fieldSVG).append('g').attr('transform', `translate(${width}, ${height-margins.bottom})`)
    var fieldSVG = d3.select(fieldSVG).style('border', '1px solid black')


    var lfLine = -Math.PI/4
    var fieldWidth = Math.PI/2
    var ofBuckets = 3
    var infBuckets = buckets.length - ofBuckets

      for(var i = 0; i < infBuckets; ++i){
        wedgePlays = buckets[i].plays.sort(function(a, b){
          return d3.ascending(a.DATE_KEY, b.DATE_KEY)
        })

        var start = lfLine+(fieldWidth/infBuckets)*i
        var end = lfLine+(fieldWidth/infBuckets)*(i+1)
        var arc = d3.arc()
          .innerRadius(0)
          .outerRadius(190)
          .startAngle(start)
          .endAngle(end);

        field.append('path')
        .attr('d', arc)
        .attr('transform', `translate(-${width/2}, 0)`)
        .attr('class', 'infWedge')
        .attr('index', i)
        .style('fill', function(d){
          val = buckets[i].plays.length/infPlaysEx
          val = val > .6 ? .6 : val
          if(!isNaN(parseFloat(val))){
            return colScale(val)
          }else{
            return 'lightgray'
          }
        })

        if(infPlays > 0){
          str = (Math.round(buckets[i].plays.length/infPlaysEx*100))+"%"
        }else{
          str = ''
        }
        fieldSVG.append('text')
        .text(str)
        .attr('x', plotDict[i][0])
        .attr('y', plotDict[i][1])
        .style('font-size', '18px')
        .style('text-anchor', 'middle')
        .style('font-weight', 'bold')
      }


      for(var i = infBuckets; i < buckets.length; i++){
        wedgePlays = buckets[i].plays.sort(function(a, b){
          return d3.ascending(a.DATE_KEY, b.DATE_KEY)
        })

        start = lfLine+(fieldWidth/ofBuckets)*(i-infBuckets)
        end = lfLine+(fieldWidth/ofBuckets)*((i-infBuckets)+1)
        arc = d3.arc()
          .innerRadius(190)
          .outerRadius(390)
          .startAngle(start)
          .endAngle(end)



        field.append('path')
        .attr('d', arc)
        .attr('transform', `translate(-${width/2}, 0)`)
        .attr('class', 'ofWedge')
        .attr('index', i)
        .style('fill', function(d){
          val = buckets[i].plays.length/ofPlays
          val = val > .6 ? .6 : val
          if(!isNaN(parseFloat(val))){
            return colScale(val)
          }else{
            return 'lightgray'
          }
        })



        if(ofPlays > 0){
          str = (Math.round(buckets[i].plays.length/ofPlays*100))+"%"
          strHR = hrBuckets[i].plays.length
        }else{
          str = ''
          strHR = ''
        }
        fieldSVG.append('text')
        .text(str)
        .attr('x', plotDict[i][0])
        .attr('y', plotDict[i][1])
        .style('font-size', '28px')
        .style('text-anchor', 'middle')
        .style('font-weight', 'bold')

        fieldSVG.append('text')
        .text(strHR)
        .attr('x', hrDict[i][0])
        .attr('y', hrDict[i][1])
        .style('font-size', '20px')
        .style('text-anchor', 'middle')
        .style('font-weight', 'bold')
      }

      fieldSVG.append('text')
      .text(name)
      .attr('x', margins.left).attr('y', margins.top*5)
      .style('font-size', '22px')

      if(career == 1){
        fieldSVG.append('text')
        .text((!!bats ? `${bats.substring(0, 1) === 'B' ? 'S' : bats.substring(0, 1)} | ` : '') + `#${num}` + ' | Career')
        .attr('x', margins.left).attr('y', margins.top*9)
        .style('font-size', '18px')
      }else{
        fieldSVG.append('text')
        .text((!!bats ? `${bats.substring(0, 1) === 'B' ? 'S' : bats.substring(0, 1)} | ` : '') + `#${num}` + (plays.length > 0 ? ` | ${String(plays[0].YEAR)}`: ''))
        .attr('x', margins.left).attr('y', margins.top*9)
        .style('font-size', '18px')
      }


      fieldSVG.append('text')
      .text(`Tot. INF BIP: ${infPlays}`)
      .attr('x', width - margins.right).attr('y', margins.top*9)
      .style('font-size', '22px')
      .style('text-anchor', 'end')

      fieldSVG.append('text')
      .text(`Tot. OF BIP: ${ofPlays}`)
      .attr('x', width - margins.right).attr('y', margins.top*5)
      .style('font-size', '22px')
      .style('text-anchor', 'end')


      var outMap = []
      for(i = 0; i < outcomes.length; ++i){
        outMap.push({'index': i, 'outcome': outcomes[i], 'num': plays.filter(function(d){ return d.OUTCOME == outcomes[i]}).length})
      }

      fieldSVG.selectAll(".hitHead")
       .data(outMap.filter(function(d){ return ['1B', '2B', '3B', 'HR'].indexOf(d.outcome) > -1}))
       .enter()
       .append("text")
       .attr('class','hitHead')
       .text(function (d) {return outNameMap[d.outcome]})
       .attr('x', function(d){return 35*(d.index)+25})
       .attr('y', height - 30)
       .style('color', 'black')
       .style('font-size', '18px')
       .style('text-decoration', 'underline')
       .style('font-weight', 'bold')
       .style('text-anchor', 'middle')

       fieldSVG.selectAll(".hitText")
        .data(outMap.filter(function(d){ return ['1B', '2B', '3B', 'HR'].indexOf(d.outcome) > -1}))
        .enter()
        .append("text")
        .attr('class','hitText')
        .text(function (d) {return d.num})
        .attr('x', function(d){return 35*(d.index)+25})
        .attr('y', height - 10)
        .style('color', 'black')
        .style('font-size', '18px')
        .style('text-anchor', 'middle')


        fieldSVG.selectAll(".typeHead")
         .data(outMap.filter(function(d){ return ['GB', 'FB', 'LD'].indexOf(d.outcome) > -1}))
         .enter()
         .append("text")
         .attr('class', 'typeHead')
         .text(function (d) {return outNameMap[d.outcome]})
         .attr('x', function(d){return 35*(d.index-4)+25})
         .attr('y', height - 75)
         .style('color', 'black')
         .style('font-size', '18px')
         .style('text-decoration', 'underline')
         .style('font-weight', 'bold')
         .style('text-anchor', 'middle')

         fieldSVG.selectAll(".typeText")
          .data(outMap.filter(function(d){ return ['GB', 'FB', 'LD'].indexOf(d.outcome) > -1}))
          .enter()
          .append("text")
          .attr('class','typeText')
          .text(function (d) {return d.num})
          .attr('x', function(d){return 35*(d.index-4)+25})
          .attr('y', height - 55)
          .style('color', 'black')
          .style('font-size', '18px')
          .style('text-anchor', 'middle')


      d3.selectAll('tr.play')
      .append('td').html(function(d){ return String(d.DATE_KEY).substring(4,6)+'-'+String(d.DATE_KEY).substring(6,8)+'-'+String(d.DATE_KEY).substring(0,4) })
      .style('font-weight', 'bold')
      .style('width', '30%')

       d3.selectAll('tr.play')
       .append('td')
       .attr('class', 'playStr')
       .html(function(d){ return d.DESCRIPTION.length > 50 ? d.DESCRIPTION.split(';')[0].substring(0,50) + '...' : d.DESCRIPTION.split(';')[0]})
       .style('width', '70%')

       fieldSVG.selectAll(".statHead")
        .data(stats.slice(0,3))
        .enter()
        .append("text")
        .attr('class','statHead')
        .text(function (e) {return e})
        .attr('x', function(e, i){return 45*i+(width-110)})
        .attr('y', height - 75)
        .style('color', 'black')
        .style('font-size', '18px')
        .style('text-decoration', 'underline')
        .style('font-weight', 'bold')
        .style('text-anchor', 'middle')
        .style('padding-left', '3px')
        .style('padding-right', '3px')

         fieldSVG.selectAll(".statHead2")
          .data(stats.slice(3,7))
          .enter()
          .append("text")
          .attr('class','statHead2')
          .text(function (e) {return e})
          .attr('x', function(e, i){return 35*i+(width-123)})
          .attr('y', height - 30)
          .style('color', 'black')
          .style('font-size', '18px')
          .style('text-decoration', 'underline')
          .style('font-weight', 'bold')
          .style('text-anchor', 'middle')
          .style('padding-left', '3px')
          .style('padding-right', '3px')

          if(statPlayer.length > 0){
            if(career == 1){
              soloStats = d3.nest()
                 .rollup(function(leaves) {
                   pa = d3.sum(leaves, function(d){ return d.SF + d.SH + d.AB + d.BB + d.HBP + d.IBB});
                   ab = d3.sum(leaves, function(d){ return d.AB});
                   return { 'K': d3.sum(leaves, function(d){ return d.K}),
                       'BB': d3.sum(leaves, function(d){ return d.BB}),
                       'SB': d3.sum(leaves, function(d){ return d.SB}),
                       'CS': d3.sum(leaves, function(d){ return d.CS}),
                       'BA': ab == 0 ? 0 : d3.sum(leaves, function(d){ return d.BA*d.AB})/ab,
                       'OBP': pa == 0 ? 0 : d3.sum(leaves, function(d){ return d.OBP*(d.SF + d.SH + d.AB + d.BB + d.HBP + d.IBB)})/pa,
                       'SLG': ab == 0 ? 0 : d3.sum(leaves, function(d){ return d.SLG*d.AB})/ab
                   }
                 })
                 .entries(statPlayer)
              }else{
                soloStats = statPlayer[0]
              }

              fieldSVG.selectAll(".stat")
               .data(stats.slice(0,3))
               .enter()
               .append("text")
               .attr('class','stat')
               .text(function (e) {return String(d3.format('.3f')(parseFloat(soloStats[e]))).replace('0.', '.')})
               .attr('x', function(e, i){return 45*i+(width-110)})
               .attr('y', height - 55)
               .style('color', 'black')
               .style('font-size', '16px')
               .style('font-weight', 'bold')
               .style('text-anchor', 'middle')
               .style('padding-left', '3px')
               .style('padding-right', '3px')

               fieldSVG.selectAll(".stat2")
                .data(stats.slice(3,7))
                .enter()
                .append("text")
                .attr('class','stat2')
                .text(function (e) {return String(parseFloat(soloStats[e]))})
                .attr('x', function(e, i){return 35*i+(width-123)})
                .attr('y', height - 10)
                .style('color', 'black')
                .style('font-size', '16px')
                .style('font-weight', 'bold')
                .style('text-anchor', 'middle')
                .style('padding-left', '3px')
                .style('padding-right', '3px')

          }
          if(wait == 1){
            setTimeout(function(){ print(); }, 1000)
          }
}
