import Vue from 'vue';
import VueRouter from 'vue-router';

import HomeComponent from '../components/HomeComponent.vue';
import SearchInterface from '../components/SearchInterface.vue';

Vue.use(VueRouter);

const router = new VueRouter({
  mode: 'history',
  base: '/',
  routes: [
    {
      path: '/',
      component: HomeComponent,
    },
    {
      path: '/search',
      component: SearchInterface,
    },
    {
      path: '*',
      redirect: '/'
    },
  ]
});

export default router;
