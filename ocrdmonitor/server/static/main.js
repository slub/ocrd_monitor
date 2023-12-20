class ResultsView {
    constructor( container, renderResultCallback, afterRenderCallback = false ) {
      this.container = container;
      this.renderResultCallback = renderResultCallback;
      this.loader = this.initLoader()
      this.afterRenderCallback = afterRenderCallback
    }
  
    async render(url) {
        this.showLoader();
        // Storing response
        const response = await fetch(url);
    
        // Storing data in form of JSON
        let data = await response.json();
        console.log(data);
    
        this.show(data);

        if( this.afterRenderCallback ) {
            this.afterRenderCallback()
        }

        this.hideLoader();
    }
    
    show(data) {
        let content = ""
    
        if(!data.results || data.results.length == 0) {
            content = "No results were found"
        } else {
            for (let result of data.results) {
                content += this.renderResultCallback(result)
            }
        }

        this.container.innerHTML = content;
    }

    hideLoader() {
        this.loader.classList.remove("is-active");
    }

    showLoader() {
        this.loader.classList.add("is-active");
    }

    initLoader() {
        let loader = document.createElement('div');
        loader.id = 'loader';
        loader.innerHTML = '<div class="loader is-loading"></div>'
        let loaderContainer = this.container
        if(loaderContainer.tagName == 'TBODY') {
            loaderContainer = loaderContainer.parentNode
        }

        loaderContainer.parentNode.insertBefore( loader, loaderContainer);
        return document.getElementById('loader');
    }

}


function diff(time_created, time_terminated) {
    let from = moment.utc(time_created)
    let to = moment.utc()
    if( time_terminated ) {
        to = moment.utc(time_terminated) 
    }

    return moment.utc(to.diff(from)).format('HH:mm:ss')
}
